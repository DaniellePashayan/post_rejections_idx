import sys
import os
import unittest
from selenium import webdriver

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))

# 2. Add the project root to the system path
sys.path.insert(0, project_root)

from pages.login_page import LoginPage
# from pages.data_form_page import DataFormPage

TEST_USER = "autouser"
TEST_PASS = "secure123"


class TestDataEntry(unittest.TestCase):
    
    def setUp(self):
        # Initialization (Runs before each test)
        self.driver = webdriver.Chrome() # Or other browser
        self.driver.maximize_window()
        
    def test_complete_data_entry(self):
        # 1. Log in (Using the LoginPage methods)
        login_page = LoginPage(self.driver)
        login_page.navigate_to_login()
        login_page.login(TEST_USER, TEST_PASS)
        
        # Add a verification step here, like waiting for the dashboard
        
        # 2. Enter data (Using the DataFormPage methods)
        # data_form = DataFormPage(self.driver)
        # data_form.enter_data(ENTRY_NAME, ENTRY_EMAIL)
        # data_form.submit_form()
        
        # # 3. Final Verification
        # # Example: Assert that a success message is displayed
        # self.assertIn("Success", self.driver.page_source)

    def tearDown(self):
        # Cleanup (Runs after each test)
        self.driver.quit()

if __name__ == '__main__':
    unittest.main()