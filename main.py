"""Main script for processing payment rejection CSV files and posting to IDX system."""

import os
import shutil
import time
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from tqdm import tqdm

from pages.login_page import LoginPage
from pages.modals.payment_code import PaymentCodesModal
from pages.modals.reset_modal import ResetModal
from pages.open_settings import SettingsPage
from pages.open_vtb import VTBPage
from pages.post_receipts.pp_bulk import PP_Bulk
from pages.post_receipts.pp_lipp import PP_LIPP
from pages.post_receipts.pp_lipp_rejections import PP_LIPP_Rejections
from pages.post_receipts.pp_main import PICScreen_Main
from pages.pp_batch import PaymentPostingBatch
from pages.pp_select_patient import PP_SelectPatient
from utils.database import DBManager, Rejections
from utils.file_reader import InputFile
from utils.notify import send_error_notification
from utils.screenshot import ScreenshotManager

# Constants
INPUT_FILE_PATH = '//NT2KWB972SRV03/SHAREDATA/CPP-Data/CBO Westbury Managers/LEADERSHIP/Bot Folder/ORCCA Rejection Scripting'
CHROME_SCALE_FACTOR = 0.75
REMOTE_DEBUG_PORT = 9222
BATCH_OPEN_RETRY_SLEEP = 2  # seconds


def setup_logging(log_folder_path: Path) -> None:
    """Configure loguru logger with file outputs for debug and info levels.
    
    Args:
        log_folder_path: Directory where log files will be saved
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H %M")
    debug_path = log_folder_path / f"debug_{timestamp}.log"
    info_path = log_folder_path / f"info_{timestamp}.log"
    
    logger.remove()
    logger.add(
        debug_path,
        rotation="5 MB",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
        retention="3 days",
        compression="zip"
    )
    logger.add(
        info_path,
        rotation="5 MB",
        level="INFO",
        retention="3 days",
        compression="zip"
    )


def get_log_folder_path() -> Path:
    """Create and return the log folder path based on current date and time."""
    now = datetime.now()
    log_path = Path("logs") / now.strftime("%Y") / now.strftime("%Y %m") / now.strftime("%Y %m %d") / now.strftime("%Y-%m-%d %H %M")
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def get_files_to_process() -> List[str]:
    """Find CSV files to process based on current date or environment override.
    
    Returns:
        List of file paths to process
    """
    now = datetime.now()
    file_date_format = now.strftime("%m_%d_%Y")
    llerina_file_date_format = now.strftime("%m_%d_%y")
    
    file_name_override = os.getenv("FILE_NAME_OVERRIDE", "").strip()
    if file_name_override:
        file_pattern = f'*{file_name_override}*.csv'
    else:
        file_pattern = f'*{file_date_format}*.csv'
    
    files = glob(f'{INPUT_FILE_PATH}/{file_pattern}')
    files.extend(glob(f'{INPUT_FILE_PATH}/*{llerina_file_date_format}*.csv'))
    
    logger.debug(f"Files to process: {files}")
    return files


def create_chrome_driver() -> webdriver.Chrome:
    """Create and configure Chrome WebDriver based on environment settings.
    
    Returns:
        Configured Chrome WebDriver instance
    """
    options = webdriver.ChromeOptions()
    options.add_argument(f"--force-device-scale-factor={CHROME_SCALE_FACTOR}")
    options.add_argument("--start-maximized")
    
    if os.getenv("ENVIRONMENT", "").lower() == "production":
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
    else:
        # Add remote debugging for non-production
        options.add_argument(f"--remote-debugging-port={REMOTE_DEBUG_PORT}")
    
    return webdriver.Chrome(options=options)


def recover_from_fatal_error(
    driver: webdriver.Chrome,
    settings_page: SettingsPage,
    vtb: VTBPage,
    pp_batch: PaymentPostingBatch,
    login_page: LoginPage,
    group: int,
    username: str,
    password: str
) -> bool:
    """Attempt to recover from fatal error by logging out and back in.
    
    Args:
        driver: Selenium WebDriver instance
        settings_page: Settings page object
        vtb: VTB page object
        pp_batch: Payment posting batch page object
        login_page: Login page object
        group: Group number to restore
        username: IDX username
        password: IDX password
        
    Returns:
        True if recovery succeeded, False otherwise
    """
    try:
        logger.warning("Attempting recovery: logging out and back in...")
        
        # Try to logout
        try:
            settings_page.logout()
            time.sleep(2)
        except Exception as logout_error:
            logger.warning(f"Logout failed during recovery: {logout_error}")
        
        # Re-login
        login_page.navigate_to_login()
        time.sleep(2)
        
        if not login_page.login(username, password):
            logger.error("Login failed during recovery")
            return False
        
        logger.info("Successfully logged back in")
        
        # Restore group and VTB selection
        settings_page.change_group(group)
        time.sleep(1)
        
        if not vtb.validate_current_selection("Payment Posting"):
            vtb.select_vtb_option("Payment Posting")
        
        # Re-open batch
        pp_batch.open_batch()
        time.sleep(BATCH_OPEN_RETRY_SLEEP)
        
        logger.success("Recovery successful - ready to continue processing")
        return True
        
    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        return False


def process_rejection(
    rejection: Rejections,
    driver: webdriver.Chrome,
    screenshot_manager: ScreenshotManager,
    db_manager: DBManager,
    batch_number: str,
    pp_batch: PaymentPostingBatch
) -> bool:
    """Process a single rejection record.
    
    Args:
        rejection: The rejection record to process
        driver: Selenium WebDriver instance
        screenshot_manager: Screenshot manager for error capture
        db_manager: Database manager for persistence
        batch_number: Current batch number
        pp_batch: Payment posting batch page object
        
    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        rejection.BatchNumber = batch_number
        logger.info(f"Processing patient: {rejection.InvoiceNumber} in batch: {batch_number}")

        # Select patient
        select_patient = PP_SelectPatient(driver, screenshot_manager)
        select_patient.reset_patient()
        patient_changed = select_patient.select_patient(str(rejection.InvoiceNumber))
        
        if patient_changed is not True and patient_changed:
            rejection.Comment = f"Modal detected during patient selection: {patient_changed}"
            db_manager.update_row(rejection)
            return 'group' not in patient_changed.lower()

        # Handle paycode
        if not rejection.Paycode:
            pic_screen = PICScreen_Main(driver)
            pic_screen.open_paycode_modal()
            pc_modal = PaymentCodesModal(driver)
            paycode = pc_modal.get_paycode_options()
            
            if not paycode:
                logger.warning(f"No valid paycode found for patient {rejection.InvoiceNumber}, skipping.")
                rejection.Comment = "No valid paycode found"
                db_manager.update_row(rejection)
                return False
                
            rejection.Paycode = paycode
        
        db_manager.update_row(rejection)
        
        # Enter paycode
        pic_screen = PICScreen_Main(driver)
        if not pic_screen.enter_paycode(rejection.Paycode):
            logger.warning(f"Failed to enter paycode for patient {rejection.InvoiceNumber}, skipping.")
            rejection.Comment = "Failed to enter paycode"
            db_manager.update_row(rejection)
            return False
            
        pic_screen.set_line_item_post_checkbox(rejection.LineItemPost)
        
        # Handle potential modal after checkbox
        reset_modal = ResetModal(driver, screenshot_manager)
        modal_text = reset_modal.close_if_present()
        
        if modal_text:
            logger.info(f"Modal detected during rejection entry: {modal_text}")
            if modal_text == 'Line Item Payments Only':
                if not pic_screen.enter_paycode(rejection.Paycode):
                    logger.warning(f"Failed to enter paycode for patient {rejection.InvoiceNumber}, skipping.")
                    rejection.Comment = "Failed to enter paycode"
                    db_manager.update_row(rejection)
                    return False
                pic_screen.set_line_item_post_checkbox(rejection.LineItemPost)
        
        # Process based on line item post flag
        if rejection.LineItemPost:
            posted = _process_line_item_post(rejection, driver, screenshot_manager)
        else:
            posted = _process_bulk_post(rejection, driver)
        
        if posted:
            rejection.Completed = True
            db_manager.update_row(rejection)
            return True
        else:
            logger.error(f"Failed to post for patient {rejection.InvoiceNumber}")
            screenshot_manager.capture_error_screenshot(f"Failed posting for patient {rejection.InvoiceNumber}")
            rejection.Comment = "Failed to post, did not post rejection to all lines"
            db_manager.update_row(rejection)
            pp_batch.open_batch()
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error processing patient {rejection.InvoiceNumber}: {e}")
        screenshot_manager.capture_error_screenshot(
            error_context=f"{rejection.InvoiceNumber}",
            exception=e
        )
        
        # Try to recover by opening batch
        try:
            pp_batch.open_batch()
        except Exception as recovery_error:
            logger.error(f"Failed to recover after error: {recovery_error}")
            screenshot_manager.capture_error_screenshot("Recovery attempt failed", recovery_error)
            # Don't send notification or re-raise here - let the main loop handle it
        
        return False


def _process_line_item_post(
    rejection: Rejections,
    driver: webdriver.Chrome,
    screenshot_manager: ScreenshotManager
) -> bool:
    """Process rejection using line item posting.
    
    Args:
        rejection: The rejection record to process
        driver: Selenium WebDriver instance
        screenshot_manager: Screenshot manager for error capture
        
    Returns:
        True if posting succeeded, False otherwise
    """
    pp_lipp = PP_LIPP(driver, screenshot_manager)
    starting_index, num_cpts_to_post = pp_lipp.num_rows_to_process()
    
    # Post the first rejection (pulls up pp_lipp_rejection screen)
    pp_lipp.populate_row(starting_index, rejection)
    
    pp_lipp_rej = PP_LIPP_Rejections(driver, rejection)
    pp_lipp_rej.enter_carrier(rejection.Carrier or "")
    
    reset_modal = ResetModal(driver, screenshot_manager)
    modal_text = reset_modal.close_if_present()
    if modal_text:
        logger.info(f"Modal detected during rejection entry: {modal_text}")
    
    pp_lipp_rej.close_screen()
    
    # Adjust count if needed
    if num_cpts_to_post > 1 and starting_index > 1:
        num_cpts_to_post += 1
    
    # Process remaining CPT rows
    for cpt_row in range(starting_index + 1, num_cpts_to_post + 1):
        logger.debug(f"Processing CPT row {cpt_row} of {num_cpts_to_post}")
        pp_lipp.populate_row(cpt_row, rejection)
    
    return pp_lipp.finalize_posting()


def _process_bulk_post(rejection: Rejections, driver: webdriver.Chrome) -> bool:
    """Process rejection using bulk posting.
    
    Args:
        rejection: The rejection record to process
        driver: Selenium WebDriver instance
        
    Returns:
        True if posting succeeded, False otherwise
    """
    pp_bulk = PP_Bulk(driver)
    if pp_bulk.enter_bulk_pp_screen():
        return pp_bulk.enter_rejection_remarks(rejection)
    return False


def archive_file_if_complete(
    file_path: str,
    file_name: str,
    group: int,
    db_manager: DBManager
) -> None:
    """Archive file if all rejections for the group are processed.
    
    Args:
        file_path: Full path to the file
        file_name: Base name of the file
        group: Group number
        db_manager: Database manager for checking completion status
    """
    unposted_invoices = db_manager.get_unposted_invoices(file_name, group)
    
    if unposted_invoices:
        logger.warning(
            f"Not all rejections for file {file_name} and group {group} were processed. "
            "They will not be archived."
        )
    else:
        archive_dir = Path(INPUT_FILE_PATH) / "ARCHIVE"
        archive_dir.mkdir(exist_ok=True)
        shutil.move(file_path, archive_dir / file_name)
        logger.info(f"Archived {file_name} to {archive_dir}")


def main() -> None:
    """Main entry point for the rejection processing script."""
    load_dotenv()
    
    # Setup logging
    log_folder_path = get_log_folder_path()
    setup_logging(log_folder_path)
    
    # Find files to process
    files_to_process = get_files_to_process()
    if not files_to_process:
        send_error_notification("No files to process.")
        return
    
    # Initialize WebDriver and managers
    driver = create_chrome_driver()
    screenshot_manager = ScreenshotManager(driver, str(log_folder_path))
    db_manager = DBManager()
    
    # Login
    login = LoginPage(driver, screenshot_manager)
    login.navigate_to_login()
    
    username = os.getenv("IDX_USERNAME")
    password = os.getenv("IDX_PASSWORD")
    if not username or not password:
        logger.error("Missing IDX_USERNAME or IDX_PASSWORD environment variables")
        send_error_notification("Missing login credentials")
        return
    
    if not login.login(username, password):
        logger.error("Login failed, terminating script.")
        return
    
    # Initialize page objects
    settings_page = SettingsPage(driver)
    vtb = VTBPage(driver)
    pp_batch = PaymentPostingBatch(driver)
    pic_screen = PICScreen_Main(driver)
    
    # Track consecutive failures for recovery logic
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    try:
        # Process each file
        for file_path in tqdm(files_to_process, desc="Processing input files"):
            logger.info(f"Using input file: {file_path}")
            
            input_file = InputFile(file_path, db_manager)
            input_file.load_data()
            
            # Process each group in the file
            for group, group_data in tqdm(input_file.group_data.items(), desc="Processing groups"):
                if not group_data:
                    logger.info(f"No data for group {group}, skipping.")
                    continue
                
                # Ensure correct group and VTB selection
                if pic_screen.get_current_batch_group() != group:
                    settings_page.change_group(group)
                
                if not vtb.validate_current_selection("Payment Posting"):
                    vtb.select_vtb_option("Payment Posting")
                
                # Open batch
                pp_batch.open_batch()
                batch_number = pp_batch.batch_number
                logger.info(f"Processing group {group} with batch number: {batch_number}")
                time.sleep(BATCH_OPEN_RETRY_SLEEP)
                
                # Process each rejection in the group
                for rejection in tqdm(group_data, total=len(group_data), desc=f"Processing group {group}"):
                    success = process_rejection(
                        rejection=rejection,
                        driver=driver,
                        screenshot_manager=screenshot_manager,
                        db_manager=db_manager,
                        batch_number=batch_number,
                        pp_batch=pp_batch
                    )
                    
                    # Track failures for recovery logic
                    if not success:
                        consecutive_failures += 1
                        logger.warning(f"Consecutive failures: {consecutive_failures}/{max_consecutive_failures}")
                        
                        # If we hit max consecutive failures, try full recovery
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"Hit {max_consecutive_failures} consecutive failures - attempting full recovery")
                            send_error_notification(f"Attempting recovery after {consecutive_failures} consecutive failures")
                            
                            if recover_from_fatal_error(
                                driver=driver,
                                settings_page=settings_page,
                                vtb=vtb,
                                pp_batch=pp_batch,
                                login_page=login,
                                group=group,
                                username=username,
                                password=password
                            ):
                                # Recovery successful - update batch number and reset counter
                                batch_number = pp_batch.batch_number
                                logger.info(f"Recovery successful - continuing with batch: {batch_number}")
                                consecutive_failures = 0
                            else:
                                # Recovery failed - send notification and break
                                logger.critical("Recovery failed - stopping processing for this group")
                                send_error_notification("FATAL ERROR: Recovery failed after multiple attempts")
                                break
                    else:
                        # Reset counter on success
                        consecutive_failures = 0
                
                # Archive file if all rejections completed
                archive_file_if_complete(
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    group=group,
                    db_manager=db_manager
                )
    
    finally:
        # Cleanup
        settings_page.logout()
        time.sleep(5)
        driver.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("Fatal error in main")
        send_error_notification(str(e))