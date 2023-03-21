from datetime import date, datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(30), nullable=False)
    second_name = Column(String(50), nullable=False)
    telegram_username = Column(String(100))
    telegram_id = Column(Integer(20), unique=True)
    date_join = Column(Date, default=date.today())
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False)
    shop = relationship('Shop', backref='users')


class Shop(Base):
    __tablename__ = 'shops'
    id = Column(Integer, primary_key=True)
    city = Column(String(30), nullable=False)


class Defective(Base):
    __tablename__ = 'defective_items'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    video_url = Column(String(200), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', backref='defective_items')
    article_number = Column(Integer)
    date = Column(Date, default=date.today())
    shop_id = Column(Integer, ForeignKey('shop.id'), nullable=False)
    shop = relationship('Shop', backref='defective_items')


class WorkShift(Base):
    __tablename__ = 'work_shifts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', backref='work_shifts')
    photo_url = Column(String(100), unique=True, nullable=False)
    status = Column(String(10), nullable=False)
    date = Column(DateTime, default=datetime.now())
    shop_id = Column(Integer, ForeignKey('shop.id'), nullable=False)
    shop = relationship('Shop', backref='work_shifts')


class Delay(Base):
    __tablename__ = 'delays'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', backref='delays')
    date = Column(DateTime, default=datetime.now())
    shop_id = Column(Integer, ForeignKey('shop.id'), nullable=False)
    shop = relationship('Shop', backref='delays')


class Spending(Base):
    __tablename__ = 'spendings'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', backref='spendings')
    date = Column(DateTime, default=datetime.now())
    photo_url = Column(String(100), nullable=False, unique=True)
    money_spent = Column(Integer, nullable=False)
    shop_id = Column(Integer, ForeignKey('shop.id'), nullable=False)
    shop = relationship('Shop', backref='spendings')
