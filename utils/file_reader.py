import pandas as pd
from loguru import logger
from utils.database import DBManager, Rejections

class InputFile:
    def __init__(self, file_path: str, db_manager: DBManager):
        self.file_path = file_path
        self.db_manager = db_manager
        self.group_data = {
            3: {},
            4: {},
            5: {},
            6: {},
        }
    
        self.load_data()
        self.write_data_to_database()

    def format_data(self):
        data = self.data.copy()
        
        # Remove leading and trailing spaces from column names
        data.columns = data.columns.str.replace(' ', '')
        
        # Replace NaN values with empty strings
        data = data.where(pd.notnull(data), '')
        
        # convert Completed column to boolean
        if 'Completed' in data.columns:
            data['Completed'] = data['Completed'].astype(bool)
        else:
            data['Completed'] = False
        
        data['FileName'] = self.file_path
                
        self.data = data
    
    def filter_by_group(self):
        if self.data is None:
            logger.error("Data not loaded. Call load_data() first.")
            return None
        
        for group_number in self.group_data.keys():
            results = self.db_manager.get_unposted_invoices(self.file_path, group_number)

            self.group_data[group_number] = results
            logger.info(f"Filtered data for group {group_number}, {len(results)} records found.")
        
    def load_data(self):
        try:
            self.data = pd.read_csv(self.file_path)
            logger.info(f"Loaded data from {self.file_path}")
            
            self.format_data()
            
            # drop any columns that have the name "COlumn" in the name
            self.data = self.data.loc[:, ~self.data.columns.str.contains('^Column', case=False)]
            
            self.filter_by_group()

        except Exception as e:
            logger.error(f"Error loading data from {self.file_path}: {e}")
    
    def write_data_to_database(self):
        rejections_list = [Rejections.model_validate(row.to_dict()) for _, row in self.data.iterrows()]
        
        self.db_manager.add_rejections(rejections_list)
    
    def update_completed_status(self, invoice_number: int):
        self.db_manager.update_completed_status(invoice_number)
