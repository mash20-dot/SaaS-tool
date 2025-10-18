from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import User, Spent
from sqlalchemy import extract, func, desc
from datetime import datetime


expenses =  Blueprint('expenses', '__name__')

@expenses.route('/add', methods=['POST', 'GET'])
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



@expenses.route('/track/all', methods=['GET', 'POST'])
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



@expenses.route('/track', methods=['GET'])
@jwt_required()
def expense_summary():
    try:
        current_email = get_jwt_identity()
        current_user = User.query.filter_by(email=current_email).first()

        if not current_user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Get filters
        date_str = request.args.get("date")
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        # If date provided, extract year/month
        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                year = parsed_date.year
                month = parsed_date.month
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400

        # Query for summary
        summary_query = (
            db.session.query(
                extract('year', Spent.date).label('year'),
                extract('month', Spent.date).label('month'),
                func.sum(Spent.amount).label('total_expenses')
            )
            .filter(Spent.user_id == current_user.id)
        )

        if year:
            summary_query = summary_query.filter(extract('year', Spent.date) == year)
        if month:
            summary_query = summary_query.filter(extract('month', Spent.date) == month)

        summary_query = summary_query.group_by('year', 'month').order_by(desc('year'), desc('month'))
        summary_results = summary_query.all()

        # Query for detailed transactions
        transactions_query = Spent.query.filter_by(user_id=current_user.id)
        if year:
            transactions_query = transactions_query.filter(extract('year', Spent.date) == year)
        if month:
            transactions_query = transactions_query.filter(extract('month', Spent.date) == month)

        transactions = transactions_query.order_by(desc(Spent.date)).all()

        if not summary_results:
            return jsonify({
                "status": "error",
                "message": f"No expense data found for year={year or 'all'}, month={month or 'all'}."
            }), 404

        # Format summary
        summary = [
            {
                "year": int(r.year),
                "month": int(r.month),
                "total_expenses": float(r.total_expenses)
            } for r in summary_results
        ]

        # Format transactions
        history = [
            {
                "expense_id": exp.id,
                "amount": float(exp.amount),
                "description": exp.description,
                "category": getattr(exp, "category", None),
                "date": exp.date.isoformat()
            } for exp in transactions
        ]

        return jsonify({
            "status": "success",
            "filter_used": {"date": date_str, "year": year, "month": month},
            "monthly_expense_summary": summary,
            "expenses_history": history,
            "user": current_email
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
