from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger
from typing import Tuple

from utils.database import Rejections
from pages.post_receipts.post_dropdown import PostDropdown
from utils.screenshot import ScreenshotManager

class PP_LIPP:
    APPROVED_FIELD_BASE = 'sBf33r'
    REJECTION_FIELD_BASE = 'sBf25r'
    ROW_BASE = 'sBrg1r'
    
    BULK_PMT_FIELD = (By.ID, 'sBf92')
    
    OK_BUTTON = (By.ID, 'OK')
    CANCEL_BUTTON = (By.ID, 'Cancel')

    def __init__(self, driver, screenshot_manager: ScreenshotManager = None):
        self.driver = driver
        self.screenshot_manager = screenshot_manager
    
    def num_rows_to_process(self) -> Tuple[int, int] | None:
        R1_CPT_INDEX_BASE = 'sBf8r'
        index=0
        R1_DROPDOWN_LOCATOR = None
        R1_CPT_INDEX_LOCATOR = None
        for i in range (1, 10):
            R1_CPT_INDEX_LOCATOR = (By.ID, R1_CPT_INDEX_BASE + str(i))
            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located(R1_CPT_INDEX_LOCATOR))
                index=i
                break
            except Exception:
                continue
        
        R1_DROPDOWN_LOCATOR = (By.ID, f'r{index}-button')
        first_row_dropdown = self.driver.find_element(*R1_DROPDOWN_LOCATOR).text
        first_row_cpt_index = self.driver.find_element(*R1_CPT_INDEX_LOCATOR).get_attribute('value') # type: ignore
            
        min_cpt = int(index)
        max_cpt = int(first_row_cpt_index) - int(first_row_dropdown) +1
        return (min_cpt, max_cpt)
        
    def confirm_on_rejection_screen(self):
        active_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.fe_c_tabs__label.fe_is-selected")
        for btn in active_buttons:
            if btn.text == 'Line Item Payment Posting':
                return True
        return False
    
    def populate_row(self, row_number: int, rejection: Rejections):
        rejection_locator = (By.ID, f'{self.REJECTION_FIELD_BASE}{row_number}')
        try:
            row_element = self.driver.find_element(By.ID, self.ROW_BASE + str(row_number))
        except Exception:
            # Try to scroll to make the row visible
            try:
                # First try scrolling to the previous row
                previous_row_id = self.ROW_BASE + str(row_number - 1)
                previous_element = self.driver.find_element(By.ID, previous_row_id)
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'top'});", previous_element)
                time.sleep(0.5)  # Give time for any dynamic loading
                
                # Now try to find the target row
                row_element = self.driver.find_element(By.ID, self.ROW_BASE + str(row_number))
                
            except Exception:
                # If previous row doesn't exist, try scrolling to bottom of page
                logger.warning(f"Previous row {row_number - 1} not found, scrolling to bottom")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                try:
                    row_element = self.driver.find_element(By.ID, self.ROW_BASE + str(row_number))
                except Exception:
                    logger.error(f"Row {row_number} not found even after scrolling. Available rows may be limited.")
                    raise NoSuchElementException(f"Unable to locate row {row_number} after multiple scroll attempts")
            
            except Exception as e:
                logger.error(f"Error during scroll operation for row {row_number}: {e}")
                if self.screenshot_manager:
                    self.screenshot_manager.capture_error_screenshot(f"Scroll error for row {row_number}", e)
                # Final attempt without scrolling
                try:
                    row_element = self.driver.find_element(By.ID, self.ROW_BASE + str(row_number))
                except NoSuchElementException:
                    logger.error(f"Final attempt to find row {row_number} failed")
                    if self.screenshot_manager:
                        self.screenshot_manager.capture_error_screenshot(f"Row {row_number} not found after all attempts")
                    raise
        dropdown = PostDropdown(self.driver, row_element)
        dropdown.set_value('R')

        try:
            rejection_field = WebDriverWait(self.driver, 3)\
                .until(EC.element_to_be_clickable(rejection_locator))
            rejection_field.click()
            rejection_field.clear()
            rejection_field.send_keys(rejection.RejCode1 + Keys.TAB * 2)
        except TimeoutException:
            logger.error(f"Rejection field for row {row_number} not found or not clickable.")
            if self.screenshot_manager:
                self.screenshot_manager.capture_error_screenshot(f"Rejection field timeout for row {row_number}")
    
    def finalize_posting(self):
        # ensure no cash is posted
        payment_amounts = float(self.driver.find_element(*self.BULK_PMT_FIELD).get_attribute('value'))
        if payment_amounts != 0:
            logger.error("Payment amounts field is not zeroed out.")
            self.driver.find_element(*self.CANCEL_BUTTON).click()
            return False
        else:
            self.driver.find_element(*self.OK_BUTTON).click()
            return True