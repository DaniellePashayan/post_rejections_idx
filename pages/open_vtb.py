from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from loguru import logger

class VTBPage:
    VTB_BUTTON = (By.ID, "vtbToggleButton")
    VTB_CONTAINER = (By.CSS_SELECTOR, "div.vtb-container.open")
    VTB_OPTIONS = {
        "Patient Services": (By.ID, 'IDXFC_IDXML_regPatientServices'),
        "TES": (By.ID, 'IDXFC_IDXML_NSLI_TES_HTB'),
        "TES Reports": (By.ID, 'IDXFC_IDXML_NSLI_TES_REPORTS_HTB'),
        "ETM": (By.ID, 'IDXFC_IDXML_NSLI_ETM_HTB'),
        "EDI": (By.ID, 'IDXFC_IDXML_NSLI_EDI_HTB'),
        "Payment Posting": (By.ID, 'IDXFC_IDXML_NSLI_PAYMENT_POST_HTB'),
        "BAR": (By.ID, 'IDXFC_IDXML_NSLI_BAR_HTB'),
        "BAR Reports": (By.ID, 'IDXFC_IDXML_NSLI_BAR_RPTS_HTB'),
        "DBMS": (By.ID, 'IDXFC_IDXML_NSLI_DBMS_HTB'),
        "Invoice Inquiry": (By.ID, 'IDXFC_IDXML_NSLI_INV_INQ_HTB'),
        "Dictionaries": (By.ID, 'IDXFC_IDXML_NSLI_DICTIONARIES_HTB'),
        "Eligibility": (By.ID, 'IDXFC_IDXML_NSLI_ELIGIBILITY_HTB')
    }
    
    HEADER_TEXT = (By.ID, "formHeader")
    
    def __init__(self, driver):
        self.driver = driver

    def is_vtb_open(self):
        try:
            vtb_element = self.driver.find_element(*self.VTB_CONTAINER)
            return 'open' in vtb_element.get_attribute('class')
        except:
            return False

    def toggle_vtb(self):
        self.driver.find_element(*self.VTB_BUTTON).click()

    def confirm_navigation(self):
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.HEADER_TEXT)
        )
        header_text = self.driver.find_element(*self.HEADER_TEXT).text
        if "Post Receipts" in header_text:
            return 
        else:
            raise Exception("Navigation to the selected VTB option failed.")
    
    def select_vtb_option(self, option_text):
        if not self.is_vtb_open():
            self.toggle_vtb()
        
        if option_text in self.VTB_OPTIONS:
            option_locator = self.VTB_OPTIONS[option_text]
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(option_locator)
            ).click()
        else:
            raise ValueError(f"Option '{option_text}' not found in VTB options.")
        
        self.confirm_navigation()
        time.sleep(1)
        
        if self.is_vtb_open():
            logger.debug("VTB is still open, closing it now.")
            self.toggle_vtb()