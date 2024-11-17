import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    DATABASE = 'smart_neighborhood.db'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
