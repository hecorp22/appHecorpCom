from sqlalchemy import Column, Integer, String
from app.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    account_key = Column(String, nullable=False)
    address = Column(String, nullable=False)
    name = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
