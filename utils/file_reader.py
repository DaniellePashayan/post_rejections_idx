"""CSV file reader and processor for rejection data."""

from pathlib import Path
from typing import Dict, List

import pandas as pd
from loguru import logger

from utils.database import ALLOWED_CARRIERS, DBManager, Rejections

# Constants
REQUIRED_COLUMNS = ['InvoiceNumber', 'Carrier', 'Paycode', 'LIPost', 'Group']
INVOICE_NUMBER_MIN = 100000000
INVOICE_NUMBER_MAX = 999999999


class InputFile:
    """Reads and processes rejection CSV files for database storage."""
    
    def __init__(self, file_path: str, db_manager: DBManager):
        """Initialize InputFile processor.
        
        Args:
            file_path: Path to the CSV file to process
            db_manager: Database manager instance for persistence
        """
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self.db_manager = db_manager
        self.data: pd.DataFrame = pd.DataFrame()
        self.group_data: Dict[int, List[Rejections]] = {3: [], 4: [], 5: [], 6: []}
        
        self.load_data()
        self.write_data_to_database()

    def format_data(self) -> None:
        """Format and normalize CSV data for processing."""
        data = self.data.copy()
        
        # Remove leading and trailing spaces from column names
        data.columns = data.columns.str.replace(' ', '')
        
        # Replace NaN values with empty strings
        data = data.where(pd.notnull(data), '')
        data['Paycode'] = data['Paycode'].astype(str)
        
        # Convert Completed column to boolean
        if 'Completed' in data.columns:
            data['Completed'] = data['Completed'].astype(bool)
        else:
            data['Completed'] = False
        
        data['FileName'] = self.file_name
        
        self.data = data
    
    def filter_by_group(self) -> None:
        """Filter data by group number and populate group_data dictionary."""
        if self.data.empty:
            logger.error("Data not loaded. Call load_data() first.")
            return
        
        for group_number in self.group_data.keys():
            results = self.db_manager.get_unposted_invoices(self.file_name, group_number)
            self.group_data[group_number] = results
            logger.info(f"Filtered data for group {group_number}, {len(results)} records found.")
    
    def validate_data(self) -> bool:
        """Validate data integrity and business rules.
        
        Returns:
            True if validation passes, False otherwise
        """
        # Ensure necessary columns exist
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in self.data.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return False
        
        rows_to_drop = []
        
        for idx, row in self.data.iterrows():
            # If Paycode is 901, ensure LIPost is false
            if row['Paycode'] == '901' and row['LIPost']:
                logger.warning(
                    f"Paycode is 901 but LIPost is True for InvoiceNumber: {row['InvoiceNumber']}. "
                    "Setting LIPost to False."
                )
                self.data.at[idx, 'LIPost'] = False  # type: ignore[call-overload]
            
            # If LIPost is true, ensure Carrier value is not empty
            if row['LIPost'] and not row['Carrier']:
                logger.error(
                    f"LIPost is True but Carrier is empty for InvoiceNumber: {row['InvoiceNumber']}. "
                    "Removing row."
                )
                rows_to_drop.append(idx)
                continue
            
            # Validate carrier against allowed list
            if row['Carrier'] and row['Carrier'] not in ALLOWED_CARRIERS:
                logger.error(
                    f"Invalid Carrier value: {row['Carrier']} for InvoiceNumber: {row['InvoiceNumber']}. "
                    "Removing row."
                )
                rows_to_drop.append(idx)
        
        # Drop invalid rows
        if rows_to_drop:
            self.data = self.data.drop(rows_to_drop)
            logger.warning(f"Dropped {len(rows_to_drop)} invalid rows during validation")
        
        return True
    
    def load_data(self) -> None:
        """Load and process CSV file data."""
        try:
            self.data = pd.read_csv(self.file_path)
            logger.info(f"Loaded data from {self.file_path}")
            
            self.format_data()
            
            # Drop any columns that have the name "Column" in them
            self.data = self.data.loc[:, ~self.data.columns.str.contains('^Column', case=False)]
            
            # Normalize carrier values to uppercase
            self.data['Carrier'] = self.data['Carrier'].str.upper()
            
            self.validate_data()
            self.filter_by_group()

        except Exception as e:
            logger.error(f"Error loading data from {self.file_path}: {e}")
            raise
    
    def write_data_to_database(self) -> None:
        """Convert dataframe rows to Rejections objects and write to database."""
        rejections_list = [
            Rejections.model_validate(row.to_dict())
            for _, row in self.data.iterrows()
        ]
        
        # Filter out invalid invoice numbers (must be 9 digits)
        rejections_list = [
            r for r in rejections_list
            if isinstance(r.InvoiceNumber, int) 
            and INVOICE_NUMBER_MIN <= r.InvoiceNumber <= INVOICE_NUMBER_MAX
        ]
        
        if rejections_list:
            self.db_manager.add_rejections(rejections_list)
            logger.info(f"Added {len(rejections_list)} rejections to database")
        else:
            logger.warning("No valid rejections to add to database")
    
    def update_row(self, rejection: Rejections) -> None:
        """Update a rejection record in the database.
        
        Args:
            rejection: Rejection record to update
        """
        self.db_manager.update_row(rejection)
