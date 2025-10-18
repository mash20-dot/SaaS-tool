from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import User, Spent
from sqlalchemy import extract, func, desc
from datetime import datetime


expenses =  Blueprint('expenses', '__name__')

@expenses.route('/track', methods=['POST'])
@jwt_required()
def track():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()
    
    if not current_user:
        return jsonify({"message": 
                "user not found"
            }), 400
    
    data = request.get_json()
    description = data.get("description")
    amount = data.get("amount")
    category = data.get("category", "General")

    new_expense = Spent(
        description=description,
        amount=amount,
        category=category,
        user_id=current_user.id
    )

    db.session.add(new_expense)
    db.session.commit()
    return jsonify({"message":
            "expenses added successfully"
        }), 201



@expenses.route('/track/all', methods=['GET'])
@jwt_required()
def get_expenses():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    expenses = Spent.query.filter_by(
        user_id=current_user.id).order_by(
            Spent.date.desc()).all()
   
    result = []
    for e in expenses:
        result.append({
            "description": e.description,
            "amount": e.amount,
            "category": e.category,
            "date": e.date
        })
    
    return jsonify(result), 200



@expenses.route('/track/summary', methods=['GET'])
@jwt_required()
def expense_summary():
    try:
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(email=current_email).first()

        if not current_user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        # Get optional filters from query params
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        # Validate query parameters
        if month and (month < 1 or month > 12):
            return jsonify({
                "status": "error",
                "message": "Invalid month value. Must be between 1 and 12."
            }), 400

        if year and (year < 2000 or year > datetime.utcnow().year + 1):
            return jsonify({
                "status": "error",
                "message": "Invalid year value."
            }), 400

        # Build query
        query = db.session.query(
            extract('year', Spent.date).label('year'),
            extract('month', Spent.date).label('month'),
            func.sum(Spent.amount).label('total_expenses')
        ).filter(Spent.user_id == current_user.id)

        # Apply filters if provided
        if year:
            query = query.filter(extract('year', Spent.date) == year)
        if month:
            query = query.filter(extract('month', Spent.date) == month)

        # Group and order
        query = query.group_by('year', 'month').order_by(desc('year'), desc('month'))

        results = query.all()

        if not results:
            return jsonify({
                "status": "error",
                "message": f"No expense data found for year={year or 'all'}, month={month or 'all'}."
            }), 404

        # Build response
        response_data = [
            {
                "year": int(r.year),
                "month": int(r.month),
                "total_expenses": float(r.total_expenses)
            }
            for r in results
        ]

        return jsonify({
            "status": "success",
            "filter_used": {"year": year, "month": month},
            "monthly_expense_summary": response_data,
            "user": current_email
        }), 200

    except Exception as e:
        # Catch-all error for debugging or unexpected issues
        return jsonify({
            "status": "error",
            "message": f"An error occurred while processing your request: {str(e)}"
        }), 500


@expenses.route('/track/summary', methods=['GET'])
@jwt_required()
def expense_summary():
    try:
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(email=current_email).first()

        if not current_user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        # Accept date, year, and month
        date_str = request.args.get("date")
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        # If 'date' is given, extract year & month automatically
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%Y/%m/%d")
                year = parsed_date.year
                month = parsed_date.month
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid date format. Please use YYYY/MM/DD."
                }), 400

        # Validate month and year
        if month and (month < 1 or month > 12):
            return jsonify({
                "status": "error",
                "message": "Invalid month value. Must be between 1 and 12."
            }), 400

        if year and (year < 2000 or year > datetime.utcnow().year + 1):
            return jsonify({
                "status": "error",
                "message": "Invalid year value."
            }), 400

        # Build query
        query = db.session.query(
            extract('year', Spent.date).label('year'),
            extract('month', Spent.date).label('month'),
            func.sum(Spent.amount).label('total_expenses')
        ).filter(Spent.user_id == current_user.id)

        # Apply filters if provided
        if year:
            query = query.filter(extract('year', Spent.date) == year)
        if month:
            query = query.filter(extract('month', Spent.date) == month)

        # Group and order
        query = query.group_by('year', 'month').order_by(desc('year'), desc('month'))
        results = query.all()

        if not results:
            return jsonify({
                "status": "error",
                "message": f"No expense data found for year={year or 'all'}, month={month or 'all'}."
            }), 404

        # Build response
        response_data = [
            {
                "year": int(r.year),
                "month": int(r.month),
                "total_expenses": float(r.total_expenses)
            }
            for r in results
        ]

        return jsonify({
            "status": "success",
            "filter_used": {
                "date": date_str,
                "year": year,
                "month": month
            },
            "monthly_expense_summary": response_data,
            "user": current_email
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500
