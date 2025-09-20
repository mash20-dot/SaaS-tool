from flask import Flask
from flask_jwt_extended import JWTManager
from db import db
import pymysql
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append('.')

from security.auth import security



#Telling python to use pymysql
#  as a replacement for MySQLdb
pymysql.install_as_MySQLdb()


app = Flask(__name__)

#setting up MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
# This disables SQLAlchemy's
#  event system for tracking
#  object modifications (saves memory and avoids warnings)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Initializing extensions
db.init_app(app)
jwt = JWTManager(app)


app.register_blueprint(security, url_prefix='/security')















with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)