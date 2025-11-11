
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from loguru import logger
import time

class PaymentCodesModal:
    MODAL_LOCATOR = (By.CSS_SELECTOR, 'div.fe_c_overlay__dialog.fe_c_lightbox__dialog.fe_c_lightbox__dialog--medium')
    OPTIONS_ROW_LOCATOR = (By.XPATH, "//div[contains(@class, 'ag-cell-value') and @role='gridcell']")
    
    CANCEL_BTN_LOCATOR = (By.ID, 'rcmLookupBoxButtonCancel')
    
    def __init__(self, driver):
        self.driver = driver
        
        self.confirm_modal_open()
    
    def confirm_modal_open(self, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(self.MODAL_LOCATOR)
            )
            logger.debug("Payment Codes modal is open.")
            return True
        except TimeoutException:
            logger.debug("Payment Codes modal did not open within the given time.")
            return False
    
    def close_modal(self):
        if self.confirm_modal_open():
            self.driver.find_element(*self.CANCEL_BTN_LOCATOR).click()
            self.driver.implicitly_wait(1)
            logger.debug("Payment Codes modal has been closed.")
    
    def get_paycode_options(self) -> str | None:
        time.sleep(3)
        options = self.driver.find_elements(*self.OPTIONS_ROW_LOCATOR)
        
        option_names = [option for option in options if option.get_attribute('col-id') == 'col1']
        option_codes = [option for option in options if option.get_attribute('col-id') == 'col2']

        available_options = set()
        for name, code in zip(option_names, option_codes):
            remove_filter = ['REJECTION', 'CREDITS', 'UNIDENTIFIED', 'EOB']
            if any(x in name.text.upper() for x in remove_filter):
                continue
            
            if 'MANUAL' in name.text.upper():
                available_options.add(code.text)
        
        time.sleep(1)
        self.close_modal()
        available_options = list(available_options)
        
        if not available_options:
            logger.warning("No manual payment codes found in the modal.")
        else:            
            logger.info(f"Found payment codes: {available_options}")
            
        if len(available_options) > 1:
            logger.warning("Multiple manual payment codes found; ensure the correct one is selected.")
        elif available_options == []:
            logger.warning("No available payment codes to select from.")
            return ""
        else:
            return available_options[0]