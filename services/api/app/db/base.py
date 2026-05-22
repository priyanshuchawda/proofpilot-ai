from importlib import import_module

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


import_module("app.db.models")
