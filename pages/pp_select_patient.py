from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger


class PP_SelectPatient:
    PATIENT_LOCATOR = (By.ID, "sAf1")
    INVOICE_LOCATOR = (By.ID, "sAf6")
    
    ACTIONS_BUTTON = (By.ID, 'Actions')
    ACTIONS_CODE_LIST = (By.ID, 'rcm-dbms-action-code-area')
    RESET_BUTTON = (By.ID, 'selectorActionCodeX')
    
    DECEASED_MODAL_INDICATOR = (By.CSS_SELECTOR, "div.fe_c_overlay__dialog.fe_c_modal__dialog.fe_c_modal__dialog--large.fe_c_modal__dialog--padded.fe_is-info")
    MODAL_CLOSE = (By.ID, "modalButtonOk")
    
    def __init__(self, driver):
        self.driver = driver
    
    def _confirm_field_populated(self, field_locator, expected_value, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_element(*field_locator).get_attribute("value") == expected_value
            )
            return True
        except TimeoutException:
            return False
    
    def reset_patient(self):
        patient_field = self.driver.find_element(*self.PATIENT_LOCATOR)
        patient_field_value = patient_field.get_attribute("value")
        if not patient_field_value:
            logger.debug("Patient field already empty, no reset needed.")
            return
        
        self.driver.find_element(*self.ACTIONS_BUTTON).click()

        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.ACTIONS_CODE_LIST))
        self.driver.find_element(*self.RESET_BUTTON).click()
        logger.debug("Patient field reset via Actions -> Reset.")
        patient_field = self.driver.find_element(*self.PATIENT_LOCATOR)
        patient_field_value = patient_field.get_attribute("value")
        if patient_field_value:
            patient_field.clear()
    
    def select_patient(self, invoice_number:str):  
        # if field is an int, convert to str
        if isinstance(invoice_number, int):
            invoice_number = str(invoice_number)
           
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.PATIENT_LOCATOR)
        )
        time.sleep(0.5)
            
        patient_field = self.driver.find_element(*self.PATIENT_LOCATOR)
        patient_field.clear()
        if self._confirm_field_populated(self.PATIENT_LOCATOR, ''):
            logger.debug("Patient field cleared successfully.")
            time.sleep(0.5)
            patient_field.send_keys("-" + invoice_number)
            time.sleep(0.5)
            patient_field.send_keys(Keys.TAB)
        
        self.check_for_deceased_modal()
            
        if not self._confirm_field_populated(self.INVOICE_LOCATOR, invoice_number):
            logger.error("Invoice number field not populated after entry.")
            time.sleep(0.5)
    
    def check_for_deceased_modal(self):
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located(self.DECEASED_MODAL_INDICATOR)
            )
            self.driver.find_element(*self.MODAL_CLOSE).click()
            logger.info("Modal detected and closed.")
        except TimeoutException:
            logger.debug("No modal detected.")