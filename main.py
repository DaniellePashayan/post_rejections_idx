from pages.login_page import LoginPage
from pages.open_settings import SettingsPage
from pages.open_vtb import VTBPage
from pages.post_receipts.pp_main import PICScreen_Main
from pages.post_receipts.pp_lipp import PP_LIPP
from pages.post_receipts.pp_lipp_rejections import PP_LIPP_Rejections
from pages.pp_batch import PaymentPostingBatch
from pages.modals.payment_code import PaymentCodesModal
from pages.pp_select_patient import PP_SelectPatient
from utils.file_reader import InputFile
from utils.database import DBManager, Rejections

from selenium import webdriver
from loguru import logger
from dotenv import load_dotenv
import os
from tqdm import tqdm
import time

#TODO: add pushbullet notifications
#TODO: add screenshots on errors

def main():
    load_dotenv()
    
    # save logs to file
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add("logs/debug_{time:YYYY-MM-DD}.log", rotation="5 MB", level="DEBUG")
    logger.add("logs/info_{time:YYYY-MM-DD}.log", rotation="5 MB", level="INFO")
    
    # TODO: change to dynamic file selection
    sample_file = './dev/PIC Templates/11_06_2025.csv'
    
    db_manager = DBManager()
    
    input_file = InputFile(sample_file, db_manager)
    input_file.load_data()
  
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless=new')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
  
    driver = webdriver.Chrome(options=options)
    login = LoginPage(driver)
    login.navigate_to_login()
    login.login(os.getenv("IDX_USERNAME"), os.getenv("IDX_PASSWORD"))
    
    settings_page = SettingsPage(driver)
    vtb = VTBPage(driver)
    pp_batch = PaymentPostingBatch(driver)
    pic_screen = PICScreen_Main(driver)
        
    for group, group_data in input_file.group_data.items():
        if group_data == []:
            logger.info(f"No data for group {group}, skipping.")
            continue
        
        if pic_screen.get_current_batch_group() != group:
            settings_page.change_group(group)
        
        if not vtb.validate_current_selection("Payment Posting"):
            vtb.select_vtb_option("Payment Posting")
        
        pp_batch.open_batch()
        time.sleep(2)
        
        for rejection in tqdm(group_data, total=len(group_data), desc=f"Processing {group}"):
            logger.info(f"Processing patient: {rejection.InvoiceNumber}")

            select_patient = PP_SelectPatient(driver)
            select_patient.reset_patient()
            select_patient.select_patient(rejection.InvoiceNumber)
            
            if rejection.Paycode == "":
                pic_screen.open_paycode_modal()
                pc_modal = PaymentCodesModal(driver)
                paycode = pc_modal.get_paycode_options()
                if paycode == "":
                    logger.warning(f"No valid paycode found for patient {rejection.InvoiceNumber}, skipping.")
                    continue
                rejection.Paycode = paycode

            pic_screen.enter_paycode(rejection.Paycode)
            pic_screen.set_line_item_post_checkbox(True)
            
            pp_lipp = PP_LIPP(driver)
            starting_index, num_cpts_to_post = pp_lipp.num_rows_to_process()
            
            # posting the first rejection will pull up the pp_lipp_rejection screen
            pp_lipp.populate_row(starting_index, rejection)
            
            pp_lipp_rej = PP_LIPP_Rejections(driver, rejection)
            pp_lipp_rej.enter_carrier('UNITED HEALTHCARE')
            pp_lipp_rej.close_screen()
            
            if num_cpts_to_post > 1:
                if starting_index == num_cpts_to_post:
                    num_cpts_to_post = num_cpts_to_post + 1
                
                for cpt_row in range(starting_index+1, num_cpts_to_post + 1):
                    # start at 2 since the pp_lipp_rejection screen already populated row 1
                    logger.debug(f"Processing CPT row {cpt_row} of {num_cpts_to_post}")
                    pp_lipp.populate_row(cpt_row, rejection)
            posted = pp_lipp.finalize_posting()
            if posted:
                db_manager.update_completed_status(rejection)
        break
            

if __name__ == "__main__":
    main()