from pages.login_page import LoginPage
from pages.open_settings import SettingsPage
from pages.open_vtb import VTBPage
from pages.pp_batch import PaymentPostingBatch
from pages.post_rejection import PICScreen
from utils.file_reader import InputFile

from selenium import webdriver
from loguru import logger
from dotenv import load_dotenv
import os
from tqdm import tqdm

def main():
    load_dotenv()
    
    # save logs to file
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add("logs/debug_{time:YYYY-MM-DD}.log", rotation="5 MB", level="DEBUG")
    logger.add("logs/info_{time:YYYY-MM-DD}.log", rotation="5 MB", level="INFO")
    
    sample_file = './dev/PIC Templates/1.csv'
    
    input_file = InputFile(sample_file)
    input_file.load_data()
  
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless=new')
  
    driver = webdriver.Chrome(options=options)
    login = LoginPage(driver)
    login.navigate_to_login()
    login.login(os.getenv("IDX_USERNAME"), os.getenv("IDX_PASSWORD"))
    
    settings_page = SettingsPage(driver)
    vtb = VTBPage(driver)
    pp_batch = PaymentPostingBatch(driver)
    pic_screen = PICScreen(driver)
        
    for group, group_data in input_file.group_data.items():
        if group_data.empty:
            logger.info(f"No data for group {group}, skipping.")
            continue
        
        settings_page.change_group(group) 

        if not vtb.validate_current_selection("Payment Posting"):
            vtb.select_vtb_option("Payment Posting")

        pp_batch.open_batch()
        
        for index, row in tqdm(group_data.iterrows(), desc=f"Processing group {group}"):
            pic_screen.select_patient(str(row['Invoice Number']), str(row['Paycode']))
            pic_screen.post_rejections(str(row['Rej Code 1']))

if __name__ == "__main__":
    main()