from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger
import re

from utils.database import Rejections

class PP_LIPP_Rejections:
    ACTIVE_BUTTONS = (By.CSS_SELECTOR, 'button.fe_c_tabs__label.fe_is-selected')
    CARRIER_INPUT = (By.ID, 'sAf40')
    REJECTION_FIELD_BASE = 'sAf1r'
    REMARK_FIELD_BASE = 'sAf5r'
    OK_BUTTON = (By.ID, 'OK')
    
    def __init__(self, driver, rejection: Rejections):
        self.driver = driver
        self.rejection = rejection
        self.rejection_dict = dict(rejection)
        self.on_rejection_screen = self._on_rejection_screen()
    
    def _on_rejection_screen(self):
        active_buttons = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(self.ACTIVE_BUTTONS))
        return 'Rejections' in [button.text for button in active_buttons]
    
    def _populate_input_field(self, base_locator, value):
        field_locator = (By.ID, f'{base_locator}')
        input_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(field_locator))
        input_field.click()
        input_field.clear()
        input_field.send_keys(value)
    
    def enter_carrier(self, carrier_override: str =''):
        carrier_value = self.rejection_dict.get('Carrier', carrier_override)
        logger.debug(f"Entering carrier: {carrier_value}")
        self._populate_input_field(self.CARRIER_INPUT[1], carrier_value)
        time.sleep(1)
        self.confirm_field_populated(self.CARRIER_INPUT, carrier_value)
    
    def confirm_field_populated(self, locator, expected_value):
        field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(locator))
        actual_value = field.get_attribute('value')
        return actual_value == expected_value
    
    def close_screen(self):
        self.driver.find_element(*self.OK_BUTTON).click()
    
    def post_li_rejections(self):
        # TODO: theres an error when trying to change rejection 2 from IDX, not an issue with the script
        for key, value in self.rejection_dict.items():
            if key.startswith('RejCode') and value:
                match = re.search(r'\d+$', key)
                if match:
                    index = match.group(0)
                    
                    ## POST REJECTION CODE
                    REJECTION_FIELD_LOCATOR = (By.ID, f'{self.REJECTION_FIELD_BASE}{index}')
                    curr_rej_value = driver.find_element(*REJECTION_FIELD_LOCATOR).get_attribute('value')
                    if not curr_rej_value:
                        logger.debug(f"Entering rejection code for {key}: {value}")
                        rejection_field = driver.find_element(*REJECTION_FIELD_LOCATOR)
                        logger.debug(rejection_field.get_attribute('id'))
                        rejection_field.click()
                        rejection_field.send_keys(value + Keys.TAB)
                    self.confirm_field_populated(REJECTION_FIELD_LOCATOR, value)
                    
                    ## POST REMARK CODE
                    remark_key = f'Remark{index}'
                    remark_value = self.rejection_dict.get(remark_key, '')
                    logger.debug(f"Remark for {key}: {remark_value}")
                    REMARK_FIELD_LOCATOR = (By.ID, f'{self.REMARK_FIELD_BASE}{index}')
                    remark_field = driver.find_element(*REMARK_FIELD_LOCATOR)
                    if remark_value:
                        logger.debug(f"Entering remark for {key}: {remark_value}")
                        remark_field.click()
                        remark_field.send_keys(remark_value)
                    else:
                        remark_field.click()
                        remark_field.send_keys(Keys.TAB)
                    self.confirm_field_populated(REMARK_FIELD_LOCATOR, value)
                    
                    # move to next line
                    index = int(index) + 1
                    REJECTION_FIELD_LOCATOR = (By.ID, f'{self.REJECTION_FIELD_BASE}{str(index)}')
            elif key.startswith('RejCode') and not value:
                print(f"No value for {key}")
        time.sleep(1)