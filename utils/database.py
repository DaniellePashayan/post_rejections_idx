from sqlmodel import create_engine, SQLModel, Field, Session, select, update
from typing import Optional
from pydantic import ConfigDict
import os
from loguru import logger
from typing import List

class Rejections(SQLModel, table=True, extend_existing=True):
    
    model_config = ConfigDict(populate_by_name=True)
    
    InvoiceNumber: int = Field(primary_key=True, index=True, alias="Invoice Number")
    Paycode: Optional[str] = Field(default=None, alias="Paycode")
    
    RejCode1: str = Field(alias="Rej Code 1")
    RejCode2: Optional[str] = Field(default=None, alias="Rej Code 2")
    RejCode3: Optional[str] = Field(default=None, alias="Rej Code 3")
    RejCode4: Optional[str] = Field(default=None ,alias="Rej Code 4")
    
    Remark1: Optional[str] = Field(default=None, alias="Remark 1")
    Remark2: Optional[str] = Field(default=None, alias="Remark 2")
    Remark3: Optional[str] = Field(default=None, alias="Remark 3")
    Remark4: Optional[str] = Field(default=None, alias="Remark 4")
    
    Group: int = Field(index=True)
    FileName: str = Field(primary_key=True, index=True)
    Completed: bool = Field(default=False, index=True)


class DBManager:
    URL = f'sqlite:///{os.path.join(os.getcwd(), "rejections.db")}'
    
    def __init__(self, URL=URL):
        self.engine = create_engine(URL)
    
    def get_engine(self):
        return self.engine
    
    def create_db_and_tables(self):
        try:
            SQLModel.metadata.create_all(self.engine)
            logger.success("Database and tables created successfully.")
        except Exception as e:
            logger.error(f"Error creating database and tables: {e}")
    
    def add_rejections(self, rejections: List[Rejections]):
        with Session(self.engine) as session:
            new_invoice_numbers = [r.InvoiceNumber for r in rejections]
            new_filenames = [r.FileName for r in rejections]
            
            statement = select(Rejections.InvoiceNumber)\
                .where(Rejections.InvoiceNumber.in_(new_invoice_numbers))\
                .where(Rejections.FileName.in_(new_filenames))
                
            existing_numbers = set(session.exec(statement).all())
            
            new_rejections_to_add = [
                r for r in rejections 
                if r.InvoiceNumber not in existing_numbers
            ]
            
            if new_rejections_to_add:
                session.add_all(new_rejections_to_add)
                session.commit()
                logger.success(f"Added {len(new_rejections_to_add)} new rejections to the database.")
            
    def get_unposted_invoices(self, file_name: str, group:int) -> List[Rejections]:
        with Session(self.engine) as session:
            statement = select(Rejections).where(
                Rejections.FileName == file_name,
                Rejections.Completed == 0,
                Rejections.Group == group
            )
            return session.exec(statement).all()
    
    def update_completed_status(self, rejection: Rejections):
        with Session(self.engine) as session:
            statement = update(Rejections).where(
                Rejections.InvoiceNumber.in_([rejection.InvoiceNumber])
            ).values(Completed=1)
            session.exec(statement)
            session.commit()
        

if __name__ == "__main__":
    db_manager = DBManager()
    db_manager.create_db_and_tables()