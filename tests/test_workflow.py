import sys
import os
import unittest
from selenium import webdriver

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))

# 2. Add the project root to the system path
sys.path.insert(0, project_root)

from pages.login_page import LoginPage
from pages.open_vtb import VTBPage

TEST_USER = "autouser"
TEST_PASS = "secure123"


class TestDataEntry(unittest.TestCase):
    
    def setUp(self):
        # Initialization (Runs before each test)
        self.driver = webdriver.Chrome() # Or other browser
        self.driver.maximize_window()
        
    def test_complete_process(self):
        # 1. Log in (Using the LoginPage methods)
        login_page = LoginPage(self.driver)
        login_page.navigate_to_login()
        login_page.login(TEST_USER, TEST_PASS)
        

    def tearDown(self):
        # Cleanup (Runs after each test)
        self.driver.quit()

if __name__ == '__main__':
    unittest.main()