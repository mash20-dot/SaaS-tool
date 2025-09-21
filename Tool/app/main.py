from flask import Flask
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect
from db import db
import pymysql
import os
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.append('.')

from security.auth import security
from product_view.items import product_view



#Telling python to use pymysql
#  as a replacement for MySQLdb
pymysql.install_as_MySQLdb()


app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#setting up MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
# This disables SQLAlchemy's
#  event system for tracking
#  object modifications (saves memory and avoids warnings)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CSRF protection globally
csrf = CSRFProtect(app)

app.register_blueprint(security, url_prefix='/security')
app.register_blueprint(product_view, url_prefix='/product_view')

from security.auth import signup, login
csrf.exempt(signup)
csrf.exempt(login)
# Exclude specific routes
#csrf.exempt('security.login')  
#csrf.exempt('security.signup')

# Initializing extensions
db.init_app(app)
jwt = JWTManager(app)






with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)