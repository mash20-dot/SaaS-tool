from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.db import db
from app.models import User, Spent
from sqlalchemy import extract, func, desc


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
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message":
                 "User not found"}), 404

    # Optional filters
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    query = db.session.query(
        extract('year', Spent.date).label('year'),
        extract('month', Spent.date).label('month'),
        func.sum(Spent.amount).label('total_expenses')
    ).filter(Spent.user_id == current_user.id)

    # Apply filters if provided
    if month:
        query = query.filter(
            extract('month', Spent.date) == month)
    if year:
        query = query.filter(
            extract('year', Spent.date) == year)


    query = (
    db.session.query(
        extract('year', Spent.date).label('year'),
        extract('month', Spent.date).label('month'),
        func.sum(Spent.amount).label('total_expenses')
    )
    .filter(Spent.user_id == current_user.id)
    .group_by('year', 'month')
    .order_by(desc('year'), desc('month')) 
    )
   
    results = query.all()

    response = [
        {
            "year": int(r.year),
            "month": int(r.month),
            "total_expenses": float(r.total_expenses)
        }
        for r in results
    ]

    return jsonify({
        "filter_used": {"month": month, "year": year},
        "monthly_expense_summary": response,
        "user": current_email
    }), 200

