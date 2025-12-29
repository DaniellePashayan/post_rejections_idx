from sqlmodel import create_engine, SQLModel, Field, Session, select, update, col
from sqlalchemy import CheckConstraint, and_
from typing import Optional
from pydantic import field_validator, ConfigDict
import os
from loguru import logger
from typing import List

# create validation to ensure "carrier" field matches existing carriers in the system
ALLOWED_CARRIERS = [
    "AARP", "AETNA", "AFFINITY", "ALICARE", "AMERICHOICE", "AMERIGROUP",
    "AMERIHEALTH", "ATLANTIS", "BEECH STREET", "BLUE CROSS BLUE SHIELD",
    "CARECONNECT", "CHOICE CARE", "CIGNA", "CONNECTICARE", "COVENTRY", "DEVON",
    "EASY CHOICE", "ELDERPLAN", "FIDELIS", "FIRST HEALTH", "FIRST UNITED",
    "GENERIC", "GHI", "GUARDIAN", "HEALTHCARE PARTNERS", "HEALTHFIRST",
    "HEALTHNET", "HEALTHPLUS", "HIP", "HORIZON", "HUMANA", "LIBERTY",
    "LOCAL 1199", "LOCAL 3", "MAGELLAN", "MAGNACARE", "MANAGED CARE", "MEDICAID",
    "MEDICARE", "MERITAIN", "METROPLUS", "MULTIPLAN", "NATL PREFFERED PROV NETWORK",
    "NEIGHBORHOOD", "NO FAULT", "OXFORD", "PHCS", "PHS", "SELF PAY", "TOUCHSTONE",
    "TRICARE", "UNION", "UNITED HEALTHCARE", "UNITED HEALTHCARE EMPIRE", "VYTRA",
    "WELLCARE", "WORKERS COMP", ""
]

class Rejections(SQLModel, table=True, extend_existing=True):
    __table_args__ = (
        CheckConstraint(
            # Allow NULL values by adding "OR Carrier IS NULL"
            "Carrier IN ('AARP','AETNA','AFFINITY','ALICARE','AMERICHOICE','AMERIGROUP','AMERIHEALTH','ATLANTIS','BEECH STREET','BLUE CROSS BLUE SHIELD','CARECONNECT','CHOICE CARE','CIGNA','CONNECTICARE','COVENTRY','DEVON','EASY CHOICE','ELDERPLAN','FIDELIS','FIRST HEALTH','FIRST UNITED','GENERIC','GHI','GUARDIAN','HEALTHCARE PARTNERS','HEALTHFIRST','HEALTHNET','HEALTHPLUS','HIP','HORIZON','HUMANA','LIBERTY','LOCAL 1199','LOCAL 3','MAGELLAN','MAGNACARE','MANAGED CARE','MEDICAID','MEDICARE','MERITAIN','METROPLUS','MULTIPLAN','NATL PREFFERED PROV NETWORK','NEIGHBORHOOD','NO FAULT','OXFORD','PHCS','PHS','SELF PAY','TOUCHSTONE','TRICARE','UNION','UNITED HEALTHCARE','UNITED HEALTHCARE EMPIRE','VYTRA','WELLCARE','WORKERS COMP','') OR Carrier IS NULL",
            name="carrier_allowed_values",
        ),
    )
    
    model_config = ConfigDict(populate_by_name=True) # type: ignore
    
    InvoiceNumber: int = Field(primary_key=True, index=True, alias="Invoice Number")
    Carrier: Optional[str] = Field(default='', alias="Carrier")
    LineItemPost: bool = Field(alias="LineItemPost")
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
    Comment: Optional[str] = Field(default=None)
    BatchNumber: Optional[str] = Field(default=None, index=True)

    @field_validator("Carrier")
    def validate_carrier(cls, v: Optional[str]) -> Optional[str]:
        # Allow None (NULL) values
        if v is None:
            return v
        # Validate against allowed carriers (including empty string)
        if v not in ALLOWED_CARRIERS:
            raise ValueError(f"Carrier must be one of {ALLOWED_CARRIERS} or None")
        return v

    # Accept 0/1 (and "0"/"1") values and coerce to proper booleans to
    # avoid Pydantic v2 serializer warnings when models are dumped/updated.
    @field_validator("Completed", mode="before")
    def coerce_completed(cls, v):  # type: ignore[no-untyped-def]
        # Already a boolean
        if isinstance(v, bool):
            return v
        # Integers 0/1
        if isinstance(v, int):
            return bool(v)
        # Strings like "0", "1", "true", "false"
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"0", "false", "no", ""}:
                return False
            if normalized in {"1", "true", "yes"}:
                return True
        # Fallback to Python truthiness
        return bool(v)

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
                .where(col(Rejections.InvoiceNumber).in_(new_invoice_numbers))\
                .where(col(Rejections.FileName).in_(new_filenames))
                
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
                Rejections.Completed == False,
                Rejections.Group == group,
                Rejections.Comment == None
            )
            return list(session.exec(statement).all())
    
    def update_row(self, rejection: Rejections):
        updates = rejection.model_dump(
            exclude_unset=True, 
            exclude_none=True, 
            by_alias=False      
        )
        
        # Don't update primary keys
        updates.pop("InvoiceNumber", None)
        updates.pop("FileName", None)
        
        valid_cols = {c.name for c in Rejections.__table__.columns}  # type: ignore[attr-defined]
        updates = {k: v for k, v in updates.items() if k in valid_cols}
        
        if not updates:
            return 0
        
        with Session(self.engine) as session:
            # build where clause by chaining to satisfy type-checkers and
            # ensure SQLAlchemy receives ColumnElement expressions
            # Use the table column objects for SQL expressions to satisfy
            # type-checkers and to avoid mixing Pydantic field objects with
            # SQLAlchemy column expressions.
            table_cols = getattr(Rejections, "__table__").c
            stmt = (
                update(Rejections)
                .where(
                    and_(
                        table_cols.InvoiceNumber == rejection.InvoiceNumber,
                        table_cols.FileName == rejection.FileName,
                    )
                )
                .values(**updates)
            )
            result = session.exec(stmt)
            session.commit()
            return result.rowcount or 0
        

if __name__ == "__main__":
    db_manager = DBManager()
    db_manager.create_db_and_tables()