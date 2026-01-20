from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


class BatchModal:
    CONTAINER = (By.CSS_SELECTOR, 'div.fe_c_overlay__dialog.fe_c_lightbox__dialog.fe_c_lightbox__dialog--medium')
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def _is_modal_open(self) -> bool:
        try:
            self.driver.find_element(*self.CONTAINER)
            return True
        except NoSuchElementException:
            return False
    
    def _close_modal(self):
        self.driver.find_element(By.ID, 'rcmLookupBoxButtonOk').click()
        
    
    def select_post_receipts(self):
        if self._is_modal_open():
            options = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'ag-cell-value') and @role='gridcell']")
            for option in options:
                if option.text == 'POST RECEIPTS':
                    option.click()
                    self._close_modal()
                    break
                else:
                    raise Exception("Batch modal is not open.")