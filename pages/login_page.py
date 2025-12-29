from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from loguru import logger

from utils.screenshot import ScreenshotManager

class LoginPage:
    # 1. Locators (Use a clear naming convention)
    URL = "https://nsli-prod.rcm.athenahealth.com/rcm/#cfSystem=NSLI"
    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "pfh-login-module-button-login")
    
    def __init__(self, driver, screenshot_manager: ScreenshotManager | None = None):
        self.driver = driver
        self.screenshot_manager = screenshot_manager

    # 2. Methods (Actions the user can take)
    def navigate_to_login(self):
        self.driver.get(self.URL)

    def login(self, username, password):
        # Use an explicit wait to ensure the element is ready
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.USERNAME_INPUT)
        )
        username_input = self.driver.find_element(*self.USERNAME_INPUT)
        username_input.clear()
        username_input.send_keys(username)
        
        password_input = self.driver.find_element(*self.PASSWORD_INPUT)
        password_input.clear()
        password_input.send_keys(password)
        
        self.driver.find_element(*self.LOGIN_BUTTON).click()

        try:
            error = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,"p.alert-block.error"))
            )
            error_text = error.text
            logger.error(f"Login error message: {error_text}")
            if self.screenshot_manager:
                self.screenshot_manager.capture_error_screenshot("login_failure", Exception("Login failed - error message displayed"))
            raise Exception("Login failed - invalid credentials")
        except TimeoutException:
            logger.info("Login successful - no error message detected")
            return True
    
