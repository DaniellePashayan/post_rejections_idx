from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

from utils.database import Rejections
from pages.post_receipts.post_dropdown import PostDropdown

class PP_LIPP:
    APPROVED_FIELD_BASE = 'sBf33r'
    REJECTION_FIELD_BASE = 'sBf25r'
    ROW_BASE = 'sBrg1r'
    
    BULK_PMT_FIELD = (By.ID, 'sBf92')
    
    OK_BUTTON = (By.ID, 'OK')
    CANCEL_BUTTON = (By.ID, 'Cancel')

    def __init__(self, driver):
        self.driver = driver
    
    def num_rows_to_process(self) -> int:
        R1_DROPDOWN_LOCATOR = (By.ID, 'r1-button')
        R1_CPT_INDEX_LOCATOR = (By.ID, 'sBf8r1')
        # TODO: when there is a copay, first row will be 2, not 1
        first_row_dropdown = self.driver.find_element(*R1_DROPDOWN_LOCATOR).text

        first_row_cpt_index = self.driver.find_element(*R1_CPT_INDEX_LOCATOR).get_attribute('value')
        return int(first_row_cpt_index) - int(first_row_dropdown) +1
    
    def confirm_on_rejection_screen(self):
        active_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.fe_c_tabs__label.fe_is-selected")
        for btn in active_buttons:
            if btn.text == 'Line Item Payment Posting':
                return True
        return False
    
    def populate_row(self, row_number: int, rejection: Rejections):
        rejection_locator = (By.ID, f'{self.REJECTION_FIELD_BASE}{row_number}')

        row_element = self.driver.find_element(By.ID, self.ROW_BASE + str(row_number))
        dropdown = PostDropdown(self.driver, row_element)
        dropdown.set_value('R')

        try:
            rejection_field = WebDriverWait(self.driver, 3)\
                .until(EC.element_to_be_clickable(rejection_locator))
            rejection_field.click()
            rejection_field.clear()
            rejection_field.send_keys(rejection.RejCode1 + Keys.TAB * 2)
        except TimeoutException:
            logger.error(f"Rejection field for row {row_number} not found or not clickable.")
    
    def finalize_posting(self):
        # ensure no cash is posted
        payment_amounts = float(self.driver.find_element(*self.BULK_PMT_FIELD).get_attribute('value'))
        if payment_amounts != 0:
            logger.error("Payment amounts field is not zeroed out.")
            self.driver.find_element(*self.CANCEL_BUTTON).click()
            return False
        else:
            self.driver.find_element(*self.OK_BUTTON).click()
            return True