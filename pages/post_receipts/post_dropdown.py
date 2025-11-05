from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

class PostDropdown:
    # Locates the element that displays the current value (e.g., 'N'), relative to the main container (sBf51r3)
    CURRENT_VALUE_LOCATOR = (By.CSS_SELECTOR, 'div.rcm-select__single-value') 
    
    DROPDOWN_OPTIONS = ['', 'Y', 'N', 'R', '?'] 
    
    def __init__(self, driver, row_div):
        self.driver = driver      
        self.row_div = row_div

    def get_value(self):
        try:
            value_element = self.row_div.find_element(*self.CURRENT_VALUE_LOCATOR)
            return value_element.text.strip()
        except Exception:
            return ''

    def set_value(self, desired_value):
        current_value = self.get_value()

        if current_value == desired_value:
            return
        
        current_index = self.DROPDOWN_OPTIONS.index(current_value)
        desired_index = self.DROPDOWN_OPTIONS.index(desired_value)

        steps = desired_index - current_index
        
        keys_to_send = []
        if steps > 0:
            keys_to_send = [Keys.ARROW_DOWN] * steps
        elif steps < 0:
            keys_to_send = [Keys.ARROW_UP] * abs(steps)
            
        keys_to_send.append(Keys.ENTER)
        
        dropdown_select = self.row_div.find_element(*self.CURRENT_VALUE_LOCATOR)
        dropdown_select.click()
        time.sleep(0.5)
        
        actions = ActionChains(self.driver)
        actions.send_keys(*keys_to_send)
        actions.perform()
        
        old_value = current_value
        new_value = self.get_value()
        logger.success(f'original value = {old_value}, desired value = {desired_value}, current value after change = {new_value}')