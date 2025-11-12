from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from loguru import logger

class ResetModal:
    MODAL_INDICATOR = (By.CSS_SELECTOR, "div.fe_c_overlay__dialog.fe_c_modal__dialog.fe_c_modal__dialog--large.fe_c_modal__dialog--padded.fe_is-info")
    MODAL_CLOSE = (By.ID, "modalButtonOk")

    def __init__(self, driver):
        self.driver = driver

    def close_if_present(self, timeout=1):
        try:
            modal = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.MODAL_INDICATOR)
            )
            if "Reset" in modal.text:
                self.driver.find_element(*self.MODAL_CLOSE).click()
                logger.debug("Reset modal detected and closed.")
                return True
        except TimeoutException:
            logger.debug("No modal detected.")
            return False