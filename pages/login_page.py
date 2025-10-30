from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LoginPage:
    # 1. Locators (Use a clear naming convention)
    URL = "https://nsli-prod.rcm.athenahealth.com/rcm/#cfSystem=NSLI"
    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.ID, "pfh-login-module-button-login")
    
    def __init__(self, driver):
        self.driver = driver

    # 2. Methods (Actions the user can take)
    def navigate_to_login(self):
        self.driver.get(self.URL)

    def login(self, username, password):
        # Use an explicit wait to ensure the element is ready
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(self.USERNAME_INPUT)
        ).send_keys(username)
        
        self.driver.find_element(*self.PASSWORD_INPUT).send_keys(password)
        self.driver.find_element(*self.LOGIN_BUTTON).click()