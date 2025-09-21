from flask import request, Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity


product_view = Blueprint('product_view', '__name__')