from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import time
from loguru import logger

from pages.modals.batch_modal import BatchModal
from utils.notify import send_error_notification

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
    
    batch_number = ''
    
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
            
            if batch_number and batch_number.isdigit():
                logger.info(f"Batch number {batch_number} is open.")
                return True
        except TimeoutException:
            return False
    
    def _check_batch_fields(self) -> bool | list:
        fields_to_check = {
            "BATCH_NUMBER_FIELD": self.BATCH_NUMBER_FIELD,
            "BANK_DESPOIT_DATE_FIELD": self.BANK_DESPOIT_DATE_FIELD,
            "DESCRIPTION_FIELD": self.DESCRIPTION_FIELD,
            "PAYMENT_TYPE_FIELD": self.PAYMENT_TYPE_FIELD,
            "PAYMENTS_FIELD": self.PAYMENTS_FIELD,
            "ACTIONS_FIELD": self.ACTIONS_FIELD
        }
        
        empty_fields = []
        
        for field_name, locator_tuple in fields_to_check.items():
            try:
                # Use the locator_tuple for the wait condition
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(locator_tuple)
                )
                # Use the locator_tuple to find the element
                field_value = self.driver.find_element(*locator_tuple).get_attribute("value")
                if field_value == "":
                    empty_fields.append(field_name)
                    logger.warning(f"Field {field_name} is empty.")
                    if field_name == "ACTIONS_FIELD":
                        send_error_notification(f"Actions field is empty in batch {self.batch_number}. Cannot proceed.")
                        batch_modal = BatchModal(self.driver)
                        if batch_modal._is_modal_open():
                            batch_modal.select_post_receipts()
                    else:
                        logger.error(f"Field {field_name} is empty. Cannot proceed.")
                    return empty_fields
                
                # Log using the string key (field_name)
                logger.debug(f"Field {field_name} is present with value: {field_value}")

            except TimeoutException:
                logger.warning(f"Field {field_name} not found within timeout.")
                return False
            except Exception as e:
                logger.error(f"Error checking field {field_name}: {e}")
                return False
        return True
    
    def _populate_field(self, field_name: str) -> bool:
        """Populate a single batch field with its configured value.
        
        Args:
            field_name: Name of the field constant (e.g., "BATCH_NUMBER_FIELD")
            
        Returns:
            True if field was populated successfully, False otherwise
        """
        field_config = {
            "BATCH_NUMBER_FIELD": (self.BATCH_NUMBER_FIELD, "G"),
            "BANK_DESPOIT_DATE_FIELD": (self.BANK_DESPOIT_DATE_FIELD, "T"),
            "DESCRIPTION_FIELD": (self.DESCRIPTION_FIELD, "AUTO - PIC Scripting"),
            "PAYMENT_TYPE_FIELD": (self.PAYMENT_TYPE_FIELD, "3"),
            "PAYMENTS_FIELD": (self.PAYMENTS_FIELD, "0"),
            "ACTIONS_FIELD": (self.ACTIONS_FIELD, "O"),
        }
        
        if field_name not in field_config:
            logger.error(f"Unknown field name: {field_name}")
            return False
        
        locator, value = field_config[field_name]
        
        try:
            curr_field = self.driver.find_element(*locator)
            curr_field.click()
            curr_field.send_keys(value + Keys.TAB)
            time.sleep(0.5)
            logger.debug(f"Populated field {field_name} with value '{value}'")
            return True
        except Exception as e:
            logger.error(f"Failed to populate field {field_name}: {e}")
            return False
    
    def open_batch(self, max_retries: int = 3):
        """Open a new batch or use an existing one, with retry logic for failed field population.
        
        Args:
            max_retries: Maximum number of times to retry populating empty fields
            
        Returns:
            True if batch opened successfully, False otherwise
        """
        if not self.is_batch_open():
            logger.info("No batch is currently open. Opening a new batch.")
            time.sleep(1)
            
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.BATCH_NUMBER_FIELD)
            )
            time.sleep(3)
        
            # Initial population of all fields
            field_order = [
                "BATCH_NUMBER_FIELD",
                "BANK_DESPOIT_DATE_FIELD",
                "DESCRIPTION_FIELD",
                "PAYMENT_TYPE_FIELD",
                "PAYMENTS_FIELD",
                "ACTIONS_FIELD",
            ]
            
            for field_name in field_order:
                self._populate_field(field_name)
        else:
            # Existing batch open; ensure actions field is safely clickable.
            if not self._safe_click(self.ACTIONS_FIELD):
                logger.error("Could not focus Actions field due to persistent interception.")
                return False
        
        self.batch_number = self.driver.find_element(*self.BATCH_NUMBER_FIELD).get_attribute("value")
        logger.info(f"Batch number set to: {self.batch_number}")
        
        # Check fields and retry if any are empty
        retry_count = 0
        while retry_count < max_retries:
            batch_fields_check = self._check_batch_fields()
            
            if batch_fields_check is True:
                # All fields populated successfully
                if not self._safe_click(self.OK_BUTTON):
                    logger.error("Failed to click OK button after filling batch fields.")
                    return False
                return True
            elif isinstance(batch_fields_check, list):
                # Some fields are empty, retry populating them
                retry_count += 1
                logger.warning(f"Retry attempt {retry_count}/{max_retries} for empty fields: {batch_fields_check}")
                
                for empty_field in batch_fields_check:
                    logger.info(f"Retrying to populate field: {empty_field}")
                    self._populate_field(empty_field)
                
                # Small delay before re-checking
                time.sleep(1)
            else:
                # Unexpected return value (e.g., False from timeout)
                logger.error(f"Unexpected batch_fields_check result: {batch_fields_check}")
                return False
        
        # If we exhausted retries, log final failure
        logger.error(f"Failed to populate all batch fields after {max_retries} retries.")
        return False