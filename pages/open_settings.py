from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from loguru import logger

class SettingsPage:
    MENU_BUTTON = (By.ID, "user_menu_btn-button")
    HOG_SCREEN_LINK = (By.ID, "tools_HOG_1")
    GROUP_SELECTOR = (By.ID, "cboGroup")
    CURRENT_SELECTION = (By.CSS_SELECTOR, "[class^='rcm-select__single-value']")
    OK_BTN = (By.ID, "cmdOK")
    CANCEL_BTN = (By.ID, "cmdCancel")
    LOGOUT_BTN = (By.ID, "user_logout")
    
    GROUP_MAP = {
    "2-Grp-2 Northwell Health [CONFIDENTIAL]": 2,
    "3-Grp-3 NH Physician Partners [CONFIDENTIAL]": 3,
    "4-Grp-4 MANAGEMENT SERVICES [CONFIDENTIAL]": 4,
    "5-Grp-5 HOSPITAL SERVICES [CONFIDENTIAL]": 5,
    "6-GRP-6 ORLIN AND COHEN [CONFIDENTIAL]" :6
        }
    
    NUMBER_MAP = {v: k for k, v in GROUP_MAP.items()}
    
    def __init__(self, driver):
        self.driver = driver

    # 2. Methods (Actions the user can take)
    def _open_settings(self):
        WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located(self.MENU_BUTTON)
        ).click()

    def _open_hog_screen(self):
        self._open_settings()
        WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located(self.HOG_SCREEN_LINK)
        ).click()
    
    def logout(self):
        # check if any modal is open
        MODAL_OK = (By.ID, "modalButtonOk")
        try:
            self.driver.find_element(*MODAL_OK).click()
        except NoSuchElementException:
            pass
        self._open_settings()
        WebDriverWait(self.driver, 2).until(
            EC.presence_of_element_located(self.LOGOUT_BTN)
        ).click()
    
    def _get_current_group(self, cancel=False):
        try:
            WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(self.GROUP_SELECTOR))
        except TimeoutException:
            self._open_hog_screen()
        
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(self.GROUP_SELECTOR))
        group_selector = self.driver.find_element(*self.GROUP_SELECTOR)
        current_selection = group_selector.find_element(*self.CURRENT_SELECTION).text
        if cancel:
            cancel_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable(self.CANCEL_BTN)
            )   
            
            ActionChains(self.driver).click(cancel_button).perform()
        return self.GROUP_MAP[current_selection]
        
    def change_group(self, target_group_number: int):
        if target_group_number not in self.NUMBER_MAP:
            raise ValueError(f"Invalid target group number: {target_group_number}. Must be one of: {list(self.NUMBER_MAP.keys())}")
        
        current_group = self._get_current_group()
        
        if current_group == target_group_number:
            logger.info(f"Group {current_group} is already selected. No action needed.")
            return
        
        difference = target_group_number - current_group
        presses = abs(difference)
   
        # Define the key to send based on direction
        if difference > 0:
            # Target is a higher number, so press Down
            key_to_send = "\ue015"
        elif difference < 0:
            # Target is a lower number, so press Up
            key_to_send = "\ue013"
        else:
            cancel_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.CANCEL_BTN))
            cancel_button.click()

        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(self.GROUP_SELECTOR))
        group_selector = self.driver.find_element(*self.GROUP_SELECTOR)
        group_selector.click()
        time.sleep(0.5)
        
        # Send the arrow keys to the selector element
        for _ in range(presses):
            group_selector.send_keys(key_to_send)
            time.sleep(0.5)

        # Finally, click to confirm the selection
        group_selector.send_keys(Keys.ENTER)
        time.sleep(0.5)

        target_text = self.NUMBER_MAP[target_group_number]
        
        WebDriverWait(self.driver, 5).until(
            EC.text_to_be_present_in_element((By.ID, "cboGroup"), target_text))
        logger.success(f"Successfully changed group to {target_text}.")
        
        stale_element = self.driver.find_element(By.ID, "cboGroup")

        ok_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.OK_BTN)
        )   
        
        ActionChains(self.driver).click(ok_button).perform()
        
        WebDriverWait(self.driver, 15).until(
            EC.staleness_of(stale_element),
            message="Timeout waiting for page to navigate after save."
        )
    