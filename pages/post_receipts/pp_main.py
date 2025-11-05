from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

from pages.modals.payment_code import PaymentCodesModal

class PICScreen_Main:
    HEADER = (By.ID, "formHeader")
    PATIENT_FIELD = (By.ID, "sAf1")
    INVOICE_FIELD = (By.ID, "sAf6")
    CODE_FIELD = (By.ID, "sAf21r1")
    CODE_MAGNIFY_ICON = (By.ID, "sAf21r1-button")
    
    LI_POST_CHECKBOX = (By.XPATH, "//input[@id='sAf32r1']")
    
    def __init__(self, driver):
        self.driver = driver
    
    def in_pic_screen(self):
        try:
            time.sleep(1)
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
    
    def _in_rejection_screen(self):
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
    
    def set_line_item_post_checkbox(self, post_line_item: bool):
        def check_if_checkbox_selected(element):
            is_checked = element.is_selected()
            logger.debug(f"Checkbox selected: {is_checked}")
            return is_checked

        def toggle_checkbox(element):
            element.send_keys(Keys.SPACE)
                
        li_post_checkbox = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.LI_POST_CHECKBOX))
        is_checked = li_post_checkbox.is_selected()
        logger.debug(f"Line Item Post Checkbox selected: {is_checked}")
        
        if post_line_item:
            if not check_if_checkbox_selected(li_post_checkbox):
                toggle_checkbox(li_post_checkbox)
            self.open_line_item_posting()
        else:
            if check_if_checkbox_selected(li_post_checkbox):
                toggle_checkbox(li_post_checkbox)
    
    def enter_paycode(self, paycode:str = None): 
        if not paycode:
            self.driver.find_element(*self.CODE_MAGNIFY_ICON).click()
            payment_codes_modal = PaymentCodesModal(self.driver)
            paycode = payment_codes_modal.get_paycode_options()[0]
        
        time.sleep(0.5)
        
        code_field = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.CODE_FIELD))
        code_field.click()
        code_field.clear()
        code_field.send_keys(paycode + Keys.TAB)
        
    def open_paycode_modal(self):
        self.driver.find_element(*self.CODE_MAGNIFY_ICON).click()        
    
    def open_line_item_posting(self):
        buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.fe_c_tabs__label")
        for btn in buttons:
            if btn.text == 'Line Item Payment Posting':
                btn.click()
      

