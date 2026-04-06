from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "hecorp_schema"}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String(100), nullable=True)
    role = Column(String(50), nullable=False, default="agent")
    avatar_url = Column(Text, nullable=True)
