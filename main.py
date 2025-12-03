from pages.login_page import LoginPage
from pages.modals.payment_code import PaymentCodesModal
from pages.modals.reset_modal import ResetModal
from pages.open_settings import SettingsPage
from pages.open_vtb import VTBPage
from pages.post_receipts.pp_main import PICScreen_Main
from pages.post_receipts.pp_lipp import PP_LIPP
from pages.post_receipts.pp_lipp_rejections import PP_LIPP_Rejections
from pages.pp_batch import PaymentPostingBatch
from pages.pp_select_patient import PP_SelectPatient
from utils.database import DBManager
from utils.file_reader import InputFile
from utils.notify import send_error_notification
from utils.screenshot import ScreenshotManager

from selenium import webdriver
from loguru import logger
from dotenv import load_dotenv
import os
from tqdm import tqdm
import time as t
from datetime import datetime
from glob import glob
import shutil

def main():
    load_dotenv()
    
    # create log folder based on date
    today = datetime.now()
    year = today.strftime("%Y")
    year_month = today.strftime("%Y %m")
    year_month_day = today.strftime("%Y %m %d")
    time = today.strftime("%Y-%m-%d %H %M")
    file_date_format = today.strftime("%m_%d_%Y")
    
    log_folder_path = os.path.join("logs", year, year_month, year_month_day, time)
    os.makedirs(log_folder_path, exist_ok=True)
    
    debug_path = os.path.join(log_folder_path, f"debug_{time}.log")
    info_path = os.path.join(log_folder_path, f"info_{time}.log")
    
    logger.remove()
    logger.add(debug_path, rotation="5 MB", level="DEBUG", backtrace=True, diagnose=True, retention="3 days", compression="zip")
    logger.add(info_path, rotation="5 MB", level="INFO", retention="3 days", compression="zip")
    
    input_file_path = '//NT2KWB972SRV03/SHAREDATA/CPP-Data/CBO Westbury Managers/LEADERSHIP/Bot Folder/ORCCA Rejection Scripting'
    if os.getenv("FILE_NAME_OVERRIDE") != '' and os.getenv("FILE_NAME_OVERRIDE") is not None:
        file_name = f'*{os.getenv("FILE_NAME_OVERRIDE")}*.csv'
    else:
        file_name = f'*{file_date_format}*.csv'
    files_to_process = glob(f'{input_file_path}/{file_name}')
    logger.debug(f"Files to process: {files_to_process}")

    if files_to_process == []:
        send_error_notification("No files to process.")
        return

    for file in files_to_process:
        logger.info(f"Using input file: {file}")

        db_manager = DBManager()
        
        input_file = InputFile(file, db_manager)
        input_file.load_data()
    
        options = webdriver.ChromeOptions()
        options.add_argument("--force-device-scale-factor=0.75")
        options.add_argument("--start-maximized")
        if os.getenv("ENVIRONMENT").lower() == "production":
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        else:
            # add remote debugging for non-production
            options.add_argument("--remote-debugging-port=9222")            
    
        driver = webdriver.Chrome(options=options)
        
        # Initialize screenshot manager for error debugging
        screenshot_manager = ScreenshotManager(driver, log_folder_path)
        
        login = LoginPage(driver, screenshot_manager)
        login.navigate_to_login()
        logged_in = login.login(os.getenv("IDX_USERNAME"), os.getenv("IDX_PASSWORD"))
        if not logged_in:
            logger.error("Login failed, terminating script.")
            return
        
        settings_page = SettingsPage(driver)
        vtb = VTBPage(driver)
        pp_batch = PaymentPostingBatch(driver)
        pic_screen = PICScreen_Main(driver)
        
        for group, group_data in tqdm(input_file.group_data.items(), desc=f"Processing groups"):
            if group_data == []:
                logger.info(f"No data for group {group}, skipping.")
                continue
            
            if pic_screen.get_current_batch_group() != group:
                settings_page.change_group(group)
            
            if not vtb.validate_current_selection("Payment Posting"):
                vtb.select_vtb_option("Payment Posting")
            
            # TODO: notate batch number in DB and logs
            pp_batch.open_batch()
            t.sleep(2)
            
            for rejection in tqdm(group_data, total=len(group_data), desc=f"Processing group {group}"):
                try:
                    logger.info(f"Processing patient: {rejection.InvoiceNumber}")

                    select_patient = PP_SelectPatient(driver, screenshot_manager)
                    select_patient.reset_patient()
                    patient_changed = select_patient.select_patient(rejection.InvoiceNumber)
                    
                    if patient_changed is not True:
                        rejection.Comment = f"Modal detected during patient selection: {patient_changed}"
                        db_manager.update_row(rejection)
                        if 'group' in patient_changed.lower():
                            continue

                    if rejection.Paycode == "":
                        pic_screen.open_paycode_modal()
                        pc_modal = PaymentCodesModal(driver)
                        paycode = pc_modal.get_paycode_options()
                        if paycode == "":
                            logger.warning(f"No valid paycode found for patient {rejection.InvoiceNumber}, skipping.")
                            rejection.Comment = "No valid paycode found"
                            db_manager.update_row(rejection)
                            continue
                        rejection.Paycode = paycode
                    db_manager.update_row(rejection)
                    pc_entered = pic_screen.enter_paycode(rejection.Paycode)
                    if not pc_entered:
                        logger.warning(f"Failed to enter paycode for patient {rejection.InvoiceNumber}, skipping.")
                        rejection.Comment = "Failed to enter paycode"
                        db_manager.update_row(rejection)
                        continue
                    pic_screen.set_line_item_post_checkbox(rejection.LineItemPost)
                    # "must use line item post" modal can appear here
                    reset_modal = ResetModal(driver, screenshot_manager)
                    modal_text = reset_modal.close_if_present()
                    if modal_text is not None:
                        logger.info(f"Modal detected during rejection entry: {modal_text}")
                    
                        if modal_text == 'Line Item Payments Only':
                            pc_entered = pic_screen.enter_paycode(rejection.Paycode)
                            if not pc_entered:
                                logger.warning(f"Failed to enter paycode for patient {rejection.InvoiceNumber}, skipping.")
                                rejection.Comment = "Failed to enter paycode"
                                db_manager.update_row(rejection)
                                continue
                            pic_screen.set_line_item_post_checkbox(rejection.LineItemPost)
                    
                    pp_lipp = PP_LIPP(driver, screenshot_manager)
                    starting_index, num_cpts_to_post = pp_lipp.num_rows_to_process()
                    
                    # posting the first rejection will pull up the pp_lipp_rejection screen
                    pp_lipp.populate_row(starting_index, starting_index, num_cpts_to_post, rejection)
                    
                    pp_lipp_rej = PP_LIPP_Rejections(driver, rejection)
                    pp_lipp_rej.enter_carrier(rejection.Carrier)
                    reset_modal = ResetModal(driver, screenshot_manager)
                    modal_text = reset_modal.close_if_present()
                    if modal_text is not None:
                        logger.info(f"Modal detected during rejection entry: {modal_text}")

                    pp_lipp_rej.close_screen()
                    
                    if num_cpts_to_post > 1 and starting_index > 1:
                        num_cpts_to_post = num_cpts_to_post + 1
                    
                    for cpt_row in range(starting_index+1, num_cpts_to_post + 1):
                        # start at 2 since the pp_lipp_rejection screen already populated row 1
                        logger.debug(f"Processing CPT row {cpt_row} of {num_cpts_to_post}")
                        pp_lipp.populate_row(cpt_row, starting_index, num_cpts_to_post, rejection)
                    posted = pp_lipp.finalize_posting()
                    if posted:
                        rejection.Completed = 1
                        db_manager.update_row(rejection)
                    else:
                        logger.error(f"Failed to post for patient {rejection.InvoiceNumber}")
                        screenshot_manager.capture_error_screenshot(f"Failed posting for patient {rejection.InvoiceNumber}")
                        rejection.Comment = "Failed to post, did not post rejection to all lines"
                        db_manager.update_row(rejection)
                        pp_batch.open_batch()
                        
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
                        send_error_notification("FATAL ERROR: Unable to recover during processing.")
                        logger.error(f"Failed to recover after error: {recovery_error}")
                        screenshot_manager.capture_error_screenshot("Recovery attempt failed", recovery_error)
                        break  # Exit the loop if we can't recover
        
        # check in the db that all rows for the file name are either completed or have a comment
        unposted_invoices = db_manager.get_unposted_invoices(os.path.basename(file), group)
        if unposted_invoices:
            logger.warning(f"Not all rejections for file {os.path.basename(file)} and group {group} were processed. They will not be archived.")
            continue
        else:
            # move file to archive
            archive_dir = os.path.join(input_file_path, "ARCHIVE")
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            shutil.move(file, os.path.join(archive_dir, os.path.basename(file)))

    settings_page.logout()
    t.sleep(2)
    driver.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        send_error_notification(str(e))