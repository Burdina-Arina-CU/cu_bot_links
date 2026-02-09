from sqlalchemy import Column, BigInteger, String, Integer, Date, DateTime, ForeignKey, CheckConstraint, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    role = Column(String(10), CheckConstraint("role IN ('editor', 'user')"), default='user')
    registration_date = Column(DateTime, server_default=func.now())


class Material(Base):
    __tablename__ = 'materials'

    material_id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String(500))
    subject = Column(String(100), nullable=False)
    lesson_type = Column(String(20), nullable=False)
    teacher = Column(String(100), nullable=False)
    week = Column(Integer, CheckConstraint('week BETWEEN 1 AND 15'))
    material_type = Column(String(50), nullable=False)
    date = Column(Date)
    created_by = Column(BigInteger, ForeignKey('users.user_id'))
    created_at = Column(DateTime, server_default=func.now())


class TelegramChannelLink(Base):
    __tablename__ = 'telegram_channel_links'

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(100), nullable=False)
    teacher = Column(String(100), nullable=False)
    channel_link = Column(String(500), nullable=False)


class UserRequest(Base):
    __tablename__ = 'user_requests'

    request_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    request_text = Column(Text, nullable=False)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, server_default=func.now())
