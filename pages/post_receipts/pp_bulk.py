from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class PP_Bulk:
    STATUS_FIELD = (By.ID, 'sAf35r1')
    REJ_BASE = 'sAf1r'
    REMARK_BASE = 'sAf5r'
    OK_BTN = (By.ID, 'OK')
    
    def __init__(self, driver):
        self.driver = driver
    
    def enter_bulk_pp_screen(self):
        try:     
            status_field = self.driver.find_element(*self.STATUS_FIELD)
            status_field.click()
            status_field.send_keys(Keys.TAB * 3)
            return True
        except Exception as e:
            print(f'Error entering bulk PP screen: {e}')
            return False
    
    def close_bulk_pp_screen(self):
        try:
            ok_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(self.OK_BTN))
            ok_button.click()
            
            return True
        except Exception as e:
            print(f'Error closing bulk PP screen: {e}')
            return False
    
    def enter_rejection_remarks(self, rejection):
        for i in range(1, 5):
            try:
                if getattr(rejection, f'RejCode{i}'):
                    remark_value = getattr(rejection, f'RejCode{i}')
                    WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.ID, f'{self.REJ_BASE}{i}')))
                    self.driver.find_element(By.ID, f'{self.REJ_BASE}{i}').send_keys(remark_value + Keys.TAB)
                    
                    if getattr(rejection, f'Remark{i}'):
                        remark_value = getattr(rejection, f'Remark{i}')
                        print(f'Rejection Remark{i}: {remark_value}')
                        WebDriverWait(self.driver, 2).until(
                            EC.element_to_be_clickable((By.ID, f'{self.REMARK_BASE}{i}')))
                        self.driver.find_element(By.ID, f'{self.REMARK_BASE}{i}').send_keys(remark_value + Keys.TAB)
            except Exception as e:
                print(f'Error processing rejection remark {i}: {e}')

        # first closes the bulk screen, second files the change
        self.close_bulk_pp_screen()
        return self.close_bulk_pp_screen()