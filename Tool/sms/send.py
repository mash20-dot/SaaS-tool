from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests
from app.models import User, db, SMSHistory, SMScontacts
import os
from datetime import datetime
import re

sms = Blueprint("sms", "__name__")

cost_per_sms = float("1")
cost_per_sms_money = float("0.0465")

@sms.route('/api/sms/send', methods=['POST'])
@jwt_required()
def send_sms():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "user not found"}), 400

    data = request.get_json()
    recipients = data.get("recipients") or data.get("recipient")
    message = data.get("message")

    if not recipients or not message:
        return jsonify({
            "error": "recipients and message are required"
        }), 400

    if isinstance(recipients, str):
        recipients = [recipients]

    # Validate Ghanaian phone numbers
    gh_pattern = r"^(?:\+?233|0)[235][0-9]{8}$"
    invalid_numbers = [r for r in recipients if not re.match(gh_pattern, r)]
    if invalid_numbers:
        return jsonify({
            "error": f"Invalid Ghanaian numbers: {invalid_numbers}"
        }), 400

    # Check balance
    user_balance = float(current_user.sms_balance or 0)
    total_cost = cost_per_sms * len(recipients)

    if user_balance < total_cost:
        return jsonify({
            "message": f"Your balance is too low to send {len(recipients)} SMS. Please top up."
        }), 403

    # Prepare Arkesel API request
    url = "https://sms.arkesel.com/api/v2/sms/send"
    sender_name = current_user.business_name
    key = os.getenv("ARKESEL_SMS_KEY")
    headers = {"api-key": key, "Content-Type": "application/json"}

    # CRITICAL: Add your webhook URL here
    # This tells Arkesel where to send delivery reports
    webhook_url = os.getenv("WEBHOOK_BASE_URL") + "/sms/api/sms/dlr"

    payload = {
        "sender": sender_name,
        "message": message,
        "recipients": recipients,
        "callback_url": webhook_url  
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()

        # Check if request was successful
        if response.status_code != 200:
            return jsonify({
                "error": "Failed to send SMS",
                "details": response_data
            }), response.status_code

        # Parse Arkesel response
        arkesel_data = response_data.get("data", [])
        
        if not isinstance(arkesel_data, list):
            # Fallback: create records for all recipients
            for recipient in recipients:
                sms_log = SMSHistory(
                    user_id=current_user.id,
                    recipient=recipient,
                    message=message,
                    status="pending",
                    message_id=None,
                    created_at=datetime.utcnow()
                )
                db.session.add(sms_log)
        else:
            # Create SMS history records with Arkesel's message IDs
            for item in arkesel_data:
                message_id = item.get("message_id") or item.get("id") or item.get("messageId")
                recipient = item.get("recipient") or item.get("number") or item.get("phone")
                initial_status = item.get("status", "pending")
                
                if recipient:
                    sms_log = SMSHistory(
                        user_id=current_user.id,
                        recipient=recipient,
                        message=message,
                        status=initial_status.lower(),
                        message_id=str(message_id) if message_id else None,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(sms_log)

        db.session.commit()

        successful_count = len(arkesel_data) if isinstance(arkesel_data, list) else len(recipients)

        return jsonify({
            "message": f"SMS queued for {successful_count} recipient(s). Delivery updates will arrive soon.",
            "total_sent": successful_count,
            "total_cost": successful_count * cost_per_sms_money,
            "webhook_url": webhook_url  
        }), 200

    except requests.exceptions.RequestException as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to communicate with SMS provider",
            "details": str(e)
        }), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@sms.route("/api/sms/dlr", methods=["GET", "POST"])
def dlr_webhook():
    """
    Delivery Receipt webhook from Arkesel
    Arkesel sends: GET /api/sms/dlr?sms_id=xxx&status=DELIVERED
    """
    try:
        # Get data from query params (GET) or JSON body (POST)
        if request.method == "GET":
            message_id = request.args.get("sms_id") or request.args.get("message_id") or request.args.get("id")
            status = request.args.get("status")
        else:
            # POST request - read from JSON body
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "No data received"}), 400
            message_id = data.get("sms_id") or data.get("message_id") or data.get("id")
            status = data.get("status")

        if not message_id or not status:
            return jsonify({
                "error": "Missing required fields: message_id/sms_id and status"
            }), 400

        # Find the SMS record
        sms_record = SMSHistory.query.filter_by(message_id=str(message_id)).first()

        if not sms_record:
            return jsonify({
                "message": "Message ID not found in records"
            }), 404

        # Prevent duplicate processing
        if sms_record.status in ["delivered", "failed"]:
            return jsonify({
                "message": "Status already processed"
            }), 200

        # Update status
        new_status = status.lower()
        sms_record.status = new_status

        # Deduct balance ONLY if delivered successfully
        if new_status == "delivered":
            user = User.query.get(sms_record.user_id)
            if user:
                current_balance = float(user.sms_balance or 0)
                new_balance = round(current_balance - cost_per_sms, 2)  # Fixed floating point
                
                # Prevent negative balance (safety check)
                if new_balance < 0:
                    new_balance = 0
                
                user.sms_balance = new_balance

        db.session.commit()

        return jsonify({
            "message": "DLR processed successfully",
            "status": new_status,
            "message_id": message_id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Webhook processing failed",
            "details": str(e)
        }), 500

@sms.route('/all/sms', methods=['GET'])
@jwt_required()
def all_sms():
    """Get all SMS history for the current user"""
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({"message": "user not found"}), 400
    
    # Get all SMS records for this user
    get_all_sms_details = SMSHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(SMSHistory.created_at.desc()).all()

    # Calculate totals
    total_sms = len(get_all_sms_details)
    total_delivered = sum(1 for sms in get_all_sms_details if sms.status == "delivered")
    total_failed = sum(1 for sms in get_all_sms_details if sms.status == "failed")
    total_pending = sum(1 for sms in get_all_sms_details if sms.status == "pending")

    # Format history
    history = []
    for row in get_all_sms_details:
        history.append({
            "id": row.id,
            "status": row.status,
            "recipient": row.recipient,
            "message": row.message,
            "message_id": row.message_id,
            "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None
        })

    return jsonify({
        "balance": float(current_user.sms_balance or 0), 
        "total_sms": total_sms,
        "total_delivered": total_delivered,
        "total_failed": total_failed,
        "total_pending": total_pending,
        "history": history
    }), 200


@sms.route('/contacts', methods=['POST'])
@jwt_required()
def contacts():

    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email
    ).first()

    if not current_user:
        return jsonify({
            "message":"user not found"
        }), 400
    
    data = request.get_json()

    contact = data.get("contact")
    category = data.get("category")

    if not contact:
        return jsonify({
            "message": "contact is required"
        }), 400
    
    save = SMScontacts(
        user_id=current_user.id,
        contact=contact,
        category=category
    )
    db.session.add(save)
    db.session.commit()
    return jsonify({
        "message": "contacts saved successfully"
    }), 200

@sms.route('/all/contact', methods=['GET'])
@jwt_required()
def all_contact():
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(
        email=current_email).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    # Get all distinct recipients for this user
    all_contacts = SMScontacts.query.filter_by(
        user_id=current_user.id
    ).all()

    if not all_contacts:
        return jsonify({
            "message": "you do not have any contacts yet",
            "contacts": []
        }), 200  
    
    cont = []
    for me in all_contacts:
        cont.append({
            "user_id":current_user.id,
            "contact":me.contact,
            "category":me.category
        })
    
    return jsonify(cont), 200
