from flask_sqlalchemy import SQLAlchemy
from utils_logger import AppLogger
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

app_logger = AppLogger()




