import os
import typing

from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session

from nonebot import get_driver

from .define import *
from .base import Base


engine = create_engine(f"sqlite:///{os.path.join(get_driver().config.dict().get('data_path', 'data'), '_data.db')}")
Base.metadata.create_all(engine)

db_proxy = Session(engine)
