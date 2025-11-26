from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
from app.models import User, db, SMSHistory
import os
from datetime import datetime

sms = Blueprint("sms", "__name__")

cost_per_sms = float("0.20")

import re
from datetime import datetime

@sms.route('/api/sms/send', methods=['POST'])
@jwt_required()
def send():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message": "user not found"}), 400

    data = request.get_json()
    recipients = data.get("recipients") or data.get("recipient")
    message = data.get("message")

    if not recipients or not message:
        return jsonify({"error":
             "recipients and message are required"
        }), 400

    #making recipients a list
    if isinstance(recipients, str):
        recipients = [recipients]

    # Ghana number validation
    gh_pattern = r"^(?:\+?233|0)[235][0-9]{8}$"
    invalid_numbers = [r for r in recipients if not re.match(gh_pattern, r)]
    if invalid_numbers:
        return jsonify({
            "error": f"Invalid Ghanaian numbers: {invalid_numbers}"
        }), 400

    # Calculate total cost
    total_cost = cost_per_sms * len(recipients)
    user_balance = float(current_user.balance or 0)

    if user_balance < total_cost:
        return jsonify({
            "message": f"Your balance is too low to send {len(recipients)} SMS. Please top up."
        }), 403

    # Prepare API request
    sender_name = current_user.business_name
    url = "https://sms.arkesel.com/api/v2/sms/send"
    payload = {
        "sender": sender_name,
        "message": message,
        "recipients": recipients
    }

    key = os.getenv("ARKESEL_SMS_KEY")
    headers = {"api-key": key, "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        status_ok = response.status_code == 200 and data.get("status") == "success"

        # Log each SMS individually
        for num in recipients:
            sms_log = SMSHistory(
                user_id=current_user.id,
                recipient=num,
                message=message,
                status="success" if status_ok else "failed"
            )
            db.session.add(sms_log)

        if status_ok:
            current_user.balance = user_balance - total_cost
            db.session.commit()
            return jsonify({
                "message": f"SMS sent successfully to {len(recipients)} recipient(s), your sms is being processed at the background and will be delivered soon",
                "new_balance": float(current_user.balance),
                "arkesel_response": data
            }), 200

        db.session.commit()
        return jsonify({
            "error": "Failed to send SMS",
            "arkesel_response": data
        }), response.status_code

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@sms.route('/all/sms', methods=['GET'])
@jwt_required()
def all_sms():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    get_all_sms_details = SMSHistory.query.filter_by(
        user_id=current_user.id
    ).all()

    history = []
    for me in get_all_sms_details:
        history.append({
            "id": me.id,
            "status": me.status,
            "recipients": me.recipient,
            "message": me.message
        })
    return jsonify (history), 200