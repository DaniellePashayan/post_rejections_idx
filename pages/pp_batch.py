from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

class PaymentPostingBatch:
    BATCH_HEADER = (By.CLASS_NAME, "fe_c_tabs__label-text")
    BATCH_GROUP_TEXT = (By.ID, "formHeader")
    
    BATCH_NUMBER_FIELD = (By.ID, "sAf2")
    BANK_DESPOIT_DATE_FIELD = (By.ID, "sAf12")
    DESCRIPTION_FIELD = (By.ID, "sAf3")
    PAYMENT_TYPE_FIELD = (By.ID, "sAf16")
    PAYMENTS_FIELD = (By.ID, "sAf92")
    ACTIONS_FIELD = (By.ID, "sAf10")
    
    OK_BUTTON = (By.ID, "OK")
    
    def __init__(self, driver):
        self.driver = driver

    def _safe_click(self, locator, retries: int = 3, scroll: bool = True):
        """Attempt to click an element, handling transient overlays that intercept clicks.

        Falls back to JavaScript click if Selenium's native click keeps getting intercepted.
        """
        for attempt in range(1, retries + 1):
            try:
                element = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(locator))
                if scroll:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                element.click()
                return True
            except ElementClickInterceptedException as e:
                logger.debug(f"Click intercepted on attempt {attempt} for locator {locator}: {e}. Retrying...")
                time.sleep(0.5)
            except TimeoutException:
                logger.warning(f"Timed out waiting for element to be clickable: {locator}")
                return False
        # JS fallback
        try:
            element = self.driver.find_element(*locator)
            self.driver.execute_script("arguments[0].click();", element)
            logger.debug(f"Used JS click fallback for locator {locator}")
            return True
        except Exception as e:
            logger.error(f"Failed to click element (including JS fallback) for locator {locator}: {e}")
            return False
    
    def in_batch_page(self):
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.BATCH_HEADER)
            )
            return True
        except TimeoutException:
            return False
    
    def get_batch_group(self):
        if not self.in_batch_page():
            raise Exception("Not in Payment Posting Batch page.")
        header_text = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.BATCH_GROUP_TEXT)
        ).text
        
        # extract "Grp:X" from the header text
        parsed_text = header_text.split(" ")[2]
        group_number = int(parsed_text.split(":")[1])
        logger.info(f"Currently in batch screen for group {group_number}")

    def is_batch_open(self):
        try:
            batch_number = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.BATCH_NUMBER_FIELD)
            )
            batch_number = batch_number.get_attribute("value")
            logger.debug(f"Batch number field found with value: {batch_number}")
            if batch_number == "":
                return False
            
            if batch_number.isdigit():
                logger.info(f"Batch number {batch_number} is open.")
                return True
        except TimeoutException:
            return False
    
    def _check_batch_fields(self):
        fields_to_check = {
            "BATCH_NUMBER_FIELD": self.BATCH_NUMBER_FIELD,
            "BANK_DESPOIT_DATE_FIELD": self.BANK_DESPOIT_DATE_FIELD,
            "DESCRIPTION_FIELD": self.DESCRIPTION_FIELD,
            "PAYMENT_TYPE_FIELD": self.PAYMENT_TYPE_FIELD,
            "PAYMENTS_FIELD": self.PAYMENTS_FIELD,
            "ACTIONS_FIELD": self.ACTIONS_FIELD
        }
        for field_name, locator_tuple in fields_to_check.items():
            try:
                # Use the locator_tuple for the wait condition
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(locator_tuple)
                )
                # Use the locator_tuple to find the element
                field_value = self.driver.find_element(*locator_tuple).get_attribute("value")
                if field_value == "":
                    logger.warning(f"Field {field_name} is empty.")
                    return False
                
                # Log using the string key (field_name)
                logger.debug(f"Field {field_name} is present with value: {field_value}")

            except TimeoutException:
                logger.warning(f"Field {field_name} not found within timeout.")
                return False
            except Exception as e:
                logger.error(f"Error checking field {field_name}: {e}")
                return False
        return True
    
    def open_batch(self):
        if not self.is_batch_open():
            logger.info("No batch is currently open. Opening a new batch.")
            time.sleep(1)
            
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.BATCH_NUMBER_FIELD)
            )
            time.sleep(3)
        
            curr_field = self.driver.find_element(*self.BATCH_NUMBER_FIELD)
            curr_field.click()
            curr_field.send_keys("G" + Keys.TAB)
            time.sleep(0.5)
            
            curr_field = self.driver.find_element(*self.BANK_DESPOIT_DATE_FIELD)
            curr_field.click()
            curr_field.send_keys("T" + Keys.TAB)
            time.sleep(0.5)
            
            curr_field = self.driver.find_element(*self.DESCRIPTION_FIELD)
            curr_field.click()
            curr_field.send_keys("AUTO - PIC Scripting" + Keys.TAB)
            time.sleep(0.5)
            
            curr_field = self.driver.find_element(*self.PAYMENT_TYPE_FIELD)
            curr_field.click()
            curr_field.send_keys("3" + Keys.TAB)
            time.sleep(0.5)
            
            curr_field = self.driver.find_element(*self.PAYMENTS_FIELD)
            curr_field.click()
            curr_field.send_keys("0" + Keys.TAB)
            time.sleep(0.5)
            
            curr_field = self.driver.find_element(*self.ACTIONS_FIELD)
            curr_field.click()
            curr_field.send_keys("O" + Keys.TAB)
            time.sleep(0.5)
        else:
            # Existing batch open; ensure actions field is safely clickable.
            if not self._safe_click(self.ACTIONS_FIELD):
                logger.error("Could not focus Actions field due to persistent interception.")
                return False
        
        if self._check_batch_fields():
            if not self._safe_click(self.OK_BUTTON):
                logger.error("Failed to click OK button after filling batch fields.")
                return False
        return True