from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

class PICScreen:
    HEADER = (By.ID, "formHeader")
    PATIENT_FIELD = (By.ID, "sAf1")
    INVOICE_FIELD = (By.ID, "sAf6")
    CODE_FIELD = (By.ID, "sAf21r1")
    
    REJ1_FIELD = (By.ID, "sAf1r1")
    REJ2_FIELD = (By.ID, "sAf1r2")
    REJ3_FIELD = (By.ID, "sAf1r3")
    REJ4_FIELD = (By.ID, "sAf1r4")
    REJ5_FIELD = (By.ID, "sAf1r5")
    REJ6_FIELD = (By.ID, "sAf1r6")
    
    def __init__(self, driver):
        self.driver = driver
    
    def in_pic_screen(self):
        try:
            header = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.HEADER)
            )
            header_text = header.text
            # check if header contains "Post Receipts"
            if "Post Receipts" in header_text:
                logger.debug(f"PIC Screen header text: {header_text}")
                return True
            else:
                return False
        except TimeoutException:
            return False
    
    def _confirm_field_populated(self, locator: tuple, expected_value:str=None):
        field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(locator)
        )
        field_value = field.get_attribute("value")
        if not expected_value:
            if field_value == "":
                return False
            logger.debug(f"Field {locator} populated with value: {field_value}")
            return True
        elif field_value != expected_value:
            return False
        logger.debug(f"Field {locator} populated with value: {field_value}")
        return True
    
    def in_rejection_screen(self):
        header_text = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="tabsControlUR53-main"]/ul/li/button'))
        )
        if header_text.text == 'Rejections':
            return True
        return False
    
    def _enter_rejection_code(self, locator: tuple, code: str):
        rej_field = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(locator))
        rej_field.click()
        rej_field.clear()
        rej_field.send_keys(code + Keys.TAB)
    
    def select_patient(self, 
                       invoice_number:str, 
                       paycode:str):
        if not self.in_pic_screen():
            raise Exception("Not in PIC Screen.")
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.PATIENT_FIELD)
        )
        
        # check if theres a value in patient field
        if self._confirm_field_populated(self.PATIENT_FIELD):
            # clear and enter patient field
            self.driver.find_element(*self.PATIENT_FIELD).clear()
            time.sleep(1)
        self.driver.find_element(*self.PATIENT_FIELD).send_keys("-" + invoice_number + Keys.TAB)
        time.sleep(0.5)
            
        if not self._confirm_field_populated(self.INVOICE_FIELD, invoice_number):
            logger.error("Invoice number field not populated after entry.")
            time.sleep(0.5)
            
        if not self._confirm_field_populated(self.CODE_FIELD, paycode):
            code_field = self.driver.find_element(*self.CODE_FIELD)
            code_field.click()
            code_field.send_keys(paycode + Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB)
            time.sleep(0.5)
        
        if not self.in_rejection_screen():
            raise Exception("Not in Rejection Screen after entering invoice and paycode.")
        
    def post_rejections(self,
                        rej1:str, 
                        rej2=None, 
                        rej3=None,
                        rej4=None,
                        rej5=None,
                        rej6=None
                        ):
        
        if not self.in_rejection_screen():
            raise Exception("Not in Rejection Screen.")
        
        rejections_to_post = [
            (self.REJ1_FIELD, rej1),
            (self.REJ2_FIELD, rej2),
            (self.REJ3_FIELD, rej3),
            (self.REJ4_FIELD, rej4),
            (self.REJ5_FIELD, rej5),
            (self.REJ6_FIELD, rej6)
        ]
        
        for locator, code in rejections_to_post:
            if code:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(locator)
                )
                self._enter_rejection_code(locator, code)
                time.sleep(0.5)
        
                self._confirm_field_populated(locator, code)
        
        self.driver.find_element(By.ID, "OK").click()
        
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.CODE_FIELD)
        )
        
        self.driver.find_element(By.ID, "OK").click()