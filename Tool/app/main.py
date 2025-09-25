from flask import Flask
from flask_jwt_extended import JWTManager
from datetime import timedelta
from db import db
import pymysql
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append('.')

from security.auth import security
from product_view.items import product_view
from stock_manage.stock import stock_manage
from dashboard.dash import dashboard



#Telling python to use pymysql
#  as a replacement for MySQLdb
pymysql.install_as_MySQLdb()


app = Flask(__name__)


app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1) 

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#setting up MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
# This disables SQLAlchemy's
#  event system for tracking
#  object modifications (saves memory and avoids warnings)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.register_blueprint(security, url_prefix='/security')
app.register_blueprint(product_view, url_prefix='/product_view')
app.register_blueprint(stock_manage, url_prefix='/stock_manage')
app.register_blueprint(dashboard, url_prefix='/dashboard')



# Initializing extensions
db.init_app(app)
jwt = JWTManager(app)






with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)