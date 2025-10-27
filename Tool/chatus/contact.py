from flask import jsonify, Blueprint, request


chatus = Blueprint("chatus", "__name__")

#helper funtion to generate link
from urllib.parse import quote_plus

def make_whatsapp_link(phone, message=None):
    phone = str(phone)
    if message:
        return f"https://wa.me/{phone}?text={quote_plus(message)}"
    return f"https://wa.me/{phone}"


#route to return whatsapp link for users to chat with us
@chatus.route("/api/wa-link", methods=['POST', 'GET'])
def api_wa_link():
    phone = request.args.get("phone", "233552148347")
    message = request.args.get("message", "Hi, I need help with my nkwabiz account.")
    return jsonify({
        "whatsapp_link": make_whatsapp_link(phone, message)
    })
