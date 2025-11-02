from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
from app.models import User, db, SMSHistory
import os
from datetime import datetime

sms = Blueprint("sms", "__name__")

cost_per_sms = float("0.15")

import re
from datetime import datetime

@sms.route('/api/sms/send', methods=['POST'])
@jwt_required()
def send():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({"message":
                 "user not found"}), 400

    user_balance = float(current_user.balance or 0)
    if user_balance < cost_per_sms:
        return jsonify({"message": 
            "Your balance is too low to send an SMS. Please top up."}), 403

    data = request.get_json()
    recipient = data.get("recipient")
    message = data.get("message")

    if not recipient or not message:
        return jsonify({"error": "recipient and message are required"}), 400

    # Ghana number validation
    gh_pattern = r"^(?:\+?233|0)[235][0-9]{8}$"
    if not re.match(gh_pattern, recipient):
        return jsonify({"error": "Only Ghanaian phone numbers are allowed"}), 400

    sender_name = current_user.business_name

    url = "https://sms.arkesel.com/api/v2/sms/send"
    payload = {"sender": sender_name, "message": message, "recipients": [recipient]}

    key = os.getenv("ARKESEL_SMS_KEY")
    headers = {"api-key": key, "Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        # Log SMS regardless of success or fail
        sms_log = SMSHistory(
            user_id=current_user.id,
            recipient=recipient,
            message=message,
            status="success" if response.status_code == 200 and data.get("status") == "success" else "failed"
        )
        db.session.add(sms_log)

        if response.status_code == 200 and data.get("status") == "success":
            current_user.balance = user_balance - cost_per_sms
            db.session.commit()

            return jsonify({
                "message": "SMS sent successfully",
                "new_balance": float(current_user.balance),
                "arkesel_response": data
            }), 200

        db.session.commit()
        return jsonify({"error": "Failed to send SMS", "arkesel_response": data}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500
