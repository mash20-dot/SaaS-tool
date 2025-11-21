from flask import Flask
from flask_jwt_extended import JWTManager
from datetime import timedelta
from .db import db, app_logger, migrate
from flask_cors import CORS
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
from payment.pay import payment
from excel_export.excel import excel_export
from expenses.track import expenses
from sms.send import sms
from blog.write import blog
from forgotpassword.password import forgotpassword
from password.uppass import password


#Telling python to use pymysql
#  as a replacement for MySQLdb
pymysql.install_as_MySQLdb()


app = Flask(__name__)

from flask_cors import CORS

CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "http://localhost:4000",
            "http://localhost:5173",
            "https://nkwabiz.com",
            "https://www.nkwabiz.com",
            "https://nkwabiz-frontend-1.onrender.com",
            "https://saas-tool-mf02.onrender.com",
            "https://nkwabiz-frontend-1.onrender.com/forgot-password"
        ],
        "supports_credentials": True,
        "allow_headers": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    }
})


app_logger.init_app(app)

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=9) 

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#setting up MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
# This disables SQLAlchemy's
#  event system for tracking
#  object modifications (saves memory and avoids warnings)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PAYSTACK_SECRET_KEY'] = os.getenv('PAYSTACK_SECRET_KEY')
app.config['ARKESEL_SMS_KEY'] = os.getenv('ARKESEL_SMS_KEY')
app.config['RESEND_API_KEY'] = os.getenv('RESEND_API_KEY')


app.register_blueprint(security, url_prefix='/security')
app.register_blueprint(product_view, url_prefix='/product_view')
app.register_blueprint(stock_manage, url_prefix='/stock_manage')
app.register_blueprint(dashboard, url_prefix='/dashboard')
app.register_blueprint(payment, url_prefix='/payment')
app.register_blueprint(excel_export, url_prefix='/excel_export')
app.register_blueprint(expenses, url_prefix='/expenses')
app.register_blueprint(sms, url_prefix='/sms')
app.register_blueprint(blog, url_prefix=('/blog'))
app.register_blueprint(forgotpassword, url_prefix='/forgotpassword')
app.register_blueprint(password, url_prefix='/password')

# Initializing extensions
db.init_app(app)
jwt = JWTManager(app)
migrate.init_app(app, db)





#with app.app_context():
    #db.create_all()


if __name__ == '__main__':
    app.run(debug=False)