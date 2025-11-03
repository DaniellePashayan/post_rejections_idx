import pandas as pd
from loguru import logger

class InputFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.group_data = {
            3: {},
            4: {},
            5: {},
            6: {},
        }

    def filter_by_group(self):
        if self.data is None:
            logger.error("Data not loaded. Call load_data() first.")
            return None
        
        for group_number in self.group_data.keys():
            filtered_data = self.data[self.data['Group'] == group_number].reset_index(drop=True)
            self.group_data[group_number] = filtered_data
            logger.info(f"Filtered data for group {group_number}, {len(filtered_data)} records found.")
        return filtered_data
    
    def load_data(self):
        try:
            self.data = pd.read_csv(self.file_path)
            logger.info(f"Loaded data from {self.file_path}")
            
            # drop any columns that have the name "COlumn" in the name
            self.data = self.data.loc[:, ~self.data.columns.str.contains('^Column', case=False)]
            if 'Done' in self.data.columns:
                self.data = self.data[self.data['Done'].isna()]
            
            self.filter_by_group()

        except Exception as e:
            logger.error(f"Error loading data from {self.file_path}: {e}")