from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

from utils.database import Rejections

class PP_LIPP:
    APPROVED_FIELD_BASE = 'sBf33r'
    REJECTION_FIELD_BASE = 'sBf25r'

    def __init__(self, driver):
        self.driver = driver
    
    def confirm_on_rejection_screen(self):
        active_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.fe_c_tabs__label.fe_is-selected")
        for btn in active_buttons:
            if btn.text == 'Line Item Payment Posting':
                return True
        return False
    
    def populate_row(self, row_number: int, rejection: Rejections):
        approved_locator = (By.ID, f'{self.APPROVED_FIELD_BASE}1')
        rejection_locator = (By.ID, f'{self.REJECTION_FIELD_BASE}1')

        approved_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(approved_locator))
        rejection_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(rejection_locator))

        approved_field.click()
        approved_field.clear()
        approved_field.send_keys('0.00')

        rejection_field.click()
        rejection_field.clear()
        rejection_field.send_keys(rejection.RejCode1 + Keys.TAB)
        
        pp_lipp_rej = PP_LIPP_Rejections(driver, rejection)
        if pp_lipp_rej.on_rejection_screen:
            pp_lipp_rej.post_li_rejections()