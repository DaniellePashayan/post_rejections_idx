from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from loguru import logger

from utils.screenshot import ScreenshotManager

class ResetModal:
    MODAL_INDICATOR = (By.CSS_SELECTOR, "div.fe_c_overlay__dialog.fe_c_modal__dialog.fe_c_modal__dialog--large.fe_c_modal__dialog--padded.fe_is-info")
    MODAL_CLOSE = (By.ID, "modalButtonOk")

    def __init__(self, driver, screenshot_manager: ScreenshotManager = None):
        self.driver = driver
        self.screenshot_manager = screenshot_manager

    def close_if_present(self, timeout=2) -> str | None:
        try:
            modal = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self.MODAL_INDICATOR)
            )
            modal_text = modal.text
            if modal_text:
                WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable(self.MODAL_CLOSE)
                )
                self.driver.find_element(*self.MODAL_CLOSE).click()
                logger.debug("Reset modal detected and closed.")
                return modal_text.split("\n")[1]
        except TimeoutException:
            return