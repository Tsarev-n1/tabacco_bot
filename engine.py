from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import create_engine


async_engine = create_async_engine('sqlite:///sqlite.db')
# Поменять БД на Postgres
engine = create_engine('sqlite:///sqlite.db')
