from pages.login_page import LoginPage
from pages.open_settings import SettingsPage
from pages.open_vtb import VTBPage
from pages.pp_batch import PaymentPostingBatch
from pages.post_rejection import PICScreen
from utils.file_reader import InputFile

from selenium import webdriver

from dotenv import load_dotenv
import os

def main():
    load_dotenv()
    sample_file = '//Nasdata204/sharedata/Revenue Cycle Business Operations/Receivables Management Team/Production/Daily PICS/WORKED/PIC Scripting 10_28_2025.csv'
    
    input_file = InputFile(sample_file)
    input_file.load_data()
  
    driver = webdriver.Chrome()
    login = LoginPage(driver)
    login.navigate_to_login()
    login.login(os.getenv("IDX_USERNAME"), os.getenv("IDX_PASSWORD"))
    
    for group, group_data in input_file.group_data.items():
        settings_page = SettingsPage(driver)
        settings_page.change_group(group) 

        vtb = VTBPage(driver)
        vtb.select_vtb_option("Payment Posting")

        pp_batch = PaymentPostingBatch(driver)
        pp_batch.open_batch()
        
        if group_data.empty:
            logger.info(f"No data for group {group}, skipping.")
            continue
        
        group_data = group_data.head()
        pic_screen = PICScreen(driver)
        for index, row in group_data.iterrows():
            pic_screen.select_patient(str(row['Invoice Number']), str(row['Paycode']))
            pic_screen.post_rejections(str(row['Rej Code 1']))

if __name__ == "__main__":
    main()