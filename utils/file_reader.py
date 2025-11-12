import pandas as pd
from loguru import logger
from utils.database import DBManager, Rejections, ALLOWED_CARRIERS

class InputFile:
    def __init__(self, file_path: str, db_manager: DBManager):
        self.file_path = file_path
        self.db_manager = db_manager
        self.group_data = {
            3: [],
            4: [],
            5: [],
            6: [],
        }
    
        self.load_data()
        self.write_data_to_database()

    def format_data(self):
        data = self.data.copy()
        
        # Remove leading and trailing spaces from column names
        #! COLUMNS GET RENAMED HERE
        data.columns = data.columns.str.replace(' ', '')
        
        # Replace NaN values with empty strings
        data = data.where(pd.notnull(data), '')
        data['Paycode'] = data['Paycode'].astype(str)
        
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
    
    def validate_data(self):
        # ensure necessary columns exist
        required_columns = ['InvoiceNumber', 'Carrier', 'Paycode', 'LIPost', 'Group']
        for col in required_columns:
            if col not in self.data.columns:
                logger.error(f"Missing required column: {col}")
                return False
        
        for _, row in self.data.iterrows():
            # if Paycode is 901, ensure LIPost is false
            if row['Paycode'] == 901 and row['LIPost']:
                logger.error(f"Paycode is 901 but LIPost is True for InvoiceNumber: {row['InvoiceNumber']}")
                # change LIPost to false
                self.data.loc[self.data['InvoiceNumber'] == row['InvoiceNumber'], 'LIPost'] = False
            # if LIPost is true, ensure Carrier value is not empty
            if row['LIPost'] and not row['Carrier']:
                logger.error(f"LIPost is True but Carrier is empty for InvoiceNumber: {row['InvoiceNumber']}")
                # remove this row from data
                self.data = self.data[self.data['InvoiceNumber'] != row['InvoiceNumber']]
        
            if row['Carrier']:
                if row['Carrier'] not in ALLOWED_CARRIERS:
                    logger.error(f"Invalid Carrier value: {row['Carrier']} for InvoiceNumber: {row['InvoiceNumber']}")
                    # remove this row from data
                    self.data = self.data[self.data['InvoiceNumber'] != row['InvoiceNumber']]
        return True
    
    def load_data(self):
        try:
            self.data = pd.read_csv(self.file_path)
            logger.info(f"Loaded data from {self.file_path}")
            
            self.format_data()
            
            # drop any columns that have the name "COlumn" in the name
            self.data = self.data.loc[:, ~self.data.columns.str.contains('^Column', case=False)]
            self.validate_data()
            
            self.filter_by_group()

        except Exception as e:
            logger.error(f"Error loading data from {self.file_path}: {e}")
    
    def write_data_to_database(self):
        rejections_list = [Rejections.model_validate(row.to_dict()) for _, row in self.data.iterrows()]
        
        # remove any items where the InvoiceNumber is not a 9 digit number
        rejections_list = [r for r in rejections_list if isinstance(r.InvoiceNumber, int) and 100000000 <= r.InvoiceNumber <= 999999999]
        
        self.db_manager.add_rejections(rejections_list)
    
    def update_row(self, rejection: Rejections):
        self.db_manager.update_row(rejection)
