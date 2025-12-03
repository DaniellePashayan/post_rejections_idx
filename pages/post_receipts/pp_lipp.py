from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

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
    
    def _scroll_to_row_by_transform(self, row_number: int) -> bool:
        """
        Scroll a lazy-loaded virtualized container to reveal a specific row.
        The container uses transform: translate() on an inner div for virtual scrolling.
        Returns True if successful, False otherwise.
        """
        try:
            script = """
            // Find the outer container (with overflow: hidden)
            var container = document.querySelector('div[style*="height: 1317px"][style*="overflow: hidden"]');
            if (!container) {
                console.error('Container not found');
                return false;
            }
            
            // Find the inner div with transform
            var innerDiv = container.querySelector('div[style*="transform"]');
            if (!innerDiv) {
                console.error('Inner transform div not found');
                return false;
            }
            
            // Calculate scroll position
            // Each row is approximately 186px tall (height of each section)
            var rowNumber = arguments[0];
            var rowHeight = 186; // adjust if your rows have different heights
            var visibleHeight = 375; // only 375px visible at a time
            var containerHeight = 1317; // total container height
            
            // Calculate the Y offset needed to show this row
            // We want to position it so it's visible in the 375px viewport
            var targetY = -(rowNumber - 2) * rowHeight; // row 2 is at 0, so offset from there
            
            // Clamp to valid range
            var maxScroll = -(containerHeight - visibleHeight);
            targetY = Math.max(maxScroll, Math.min(0, targetY));
            
            // Apply the transform
            innerDiv.style.transform = 'translate(0px, ' + targetY + 'px)';
            
            // Trigger any scroll event listeners
            var event = new Event('scroll');
            container.dispatchEvent(event);
            
            console.log('Scrolled to row ' + rowNumber + ' with transform: ' + targetY + 'px');
            return true;
            """
            
            result = self.driver.execute_script(script, row_number)
            import time
            time.sleep(0.5)  # Wait for lazy loading to render the elements
            return result if result else False
            
        except Exception as e:
            logger.error(f"_scroll_to_row_by_transform failed: {e}")
            return False
    
    def populate_row(self, row_number: int, first_row_number: int, num_cpts: int, rejection: Rejections):
        rejection_locator = (By.ID, f'{self.REJECTION_FIELD_BASE}{row_number}')
        try:
            row_element = self.driver.find_element(By.ID, self.ROW_BASE + str(row_number))
            dropdown = PostDropdown(self.driver, row_element)
            dropdown.set_value('R')
            # if row_number > 1:
            #     self._scroll_to_row_by_transform(row_number)
        except Exception:
            logger.error(f"Row {row_number} not found even after scrolling. Available rows may be limited.")
            raise NoSuchElementException(f"Unable to locate row {row_number} after multiple scroll attempts")

        try:
            rejection_field = WebDriverWait(self.driver, 3)\
                .until(EC.element_to_be_clickable(rejection_locator))
            rejection_field.click()
            rejection_field.clear()
            
            if row_number > first_row_number:
                num_tabs = 2 if row_number >= num_cpts else 7
            else:
                num_tabs = 1
            rejection_field.send_keys(rejection.RejCode1 + Keys.TAB * num_tabs)

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