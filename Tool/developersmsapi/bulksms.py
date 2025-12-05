from flask import Flask, request, jsonify, Blueprint
from flask_jwt_extended import  get_jwt_identity
from functools import wraps
import requests
import hashlib
import time
from datetime import datetime, timedelta
import os
from collections import defaultdict
import hmac
import json
from threading import Thread

developersmsapi = Blueprint('developersmsapi', __name__)

# Configuration
ARKESEL_API_KEY = os.getenv('ARKESEL_API_KEY', 'your-arkesel-api-key')
ARKESEL_BASE_URL = 'https://sms.arkesel.com/api/v2/sms'
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your-webhook-secret-key')

# In-memory storage (use Redis/Database in production)
api_keys = {
    # Format: api_key: {name, tier, requests_per_minute, total_requests, created_at, webhook_url, webhook_secret}
    'demo_key_12345': {
        'name': 'Demo Client',
        'tier': 'basic',
        'rpm_limit': 10,
        'total_requests': 0,
        'created_at': datetime.now().isoformat(),
        'webhook_url': None,
        'webhook_secret': None,
        'webhook_events': ['delivered', 'failed', 'sent']
    }
}

rate_limit_tracker = defaultdict(list)
message_tracking = {}  # Track message_id to api_key mapping
webhook_logs = defaultdict(list)  # Store webhook delivery logs


def generate_webhook_signature(payload, secret):
    """Generate HMAC signature for webhook payload"""
    message = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_webhook_signature(payload, signature, secret):
    """Verify webhook signature"""
    expected_signature = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


def send_webhook(webhook_url, payload, secret, api_key):
    """Send webhook notification to client"""
    try:
        signature = generate_webhook_signature(payload, secret)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': payload.get('event'),
            'User-Agent': 'BulkSMS-Webhook/1.0'
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        # Log webhook delivery
        webhook_logs[api_key].append({
            'timestamp': datetime.now().isoformat(),
            'event': payload.get('event'),
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'message_id': payload.get('data', {}).get('message_id')
        })
        
        # Keep only last 100 logs per client
        if len(webhook_logs[api_key]) > 100:
            webhook_logs[api_key] = webhook_logs[api_key][-100:]
        
        return response.status_code == 200
        
    except Exception as e:
        webhook_logs[api_key].append({
            'timestamp': datetime.now().isoformat(),
            'event': payload.get('event'),
            'success': False,
            'error': str(e),
            'message_id': payload.get('data', {}).get('message_id')
        })
        return False


def trigger_webhook_async(api_key, event_type, data):
    """Trigger webhook asynchronously"""
    client = api_keys.get(api_key)
    
    if not client or not client.get('webhook_url'):
        return
    
    if event_type not in client.get('webhook_events', []):
        return
    
    payload = {
        'event': event_type,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    
    # Send webhook in background thread
    thread = Thread(
        target=send_webhook,
        args=(client['webhook_url'], payload, client.get('webhook_secret', ''), api_key)
    )
    thread.daemon = True
    thread.start()


def generate_api_key(client_name):
    """Generate a unique API key for a client"""
    timestamp = str(time.time())
    raw = f"{client_name}_{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def check_rate_limit(api_key):
    """Check if client has exceeded rate limit"""
    now = time.time()
    client = api_keys.get(api_key)
    
    if not client:
        return False
    
    rpm_limit = client['rpm_limit']
    
    # Remove requests older than 1 minute
    rate_limit_tracker[api_key] = [
        req_time for req_time in rate_limit_tracker[api_key]
        if now - req_time < 60
    ]
    
    # Check if limit exceeded
    if len(rate_limit_tracker[api_key]) >= rpm_limit:
        return False
    
    # Add current request
    rate_limit_tracker[api_key].append(now)
    return True


def require_api_key(f):
    """Decorator to validate API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'Missing API key',
                'message': 'Please provide X-API-Key in headers'
            }), 401
        
        if api_key not in api_keys:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        if not check_rate_limit(api_key):
            client = api_keys[api_key]
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded',
                'message': f'You have exceeded your limit of {client["rpm_limit"]} requests per minute'
            }), 429
        
        # Increment total requests
        api_keys[api_key]['total_requests'] += 1
        
        return f(*args, **kwargs)
    
    return decorated_function


@developersmsapi.route('/')
def home():
    """API documentation endpoint"""
    return jsonify({
        'name': 'Bulk SMS API',
        'version': '1.0.0',
        'endpoints': {
            'send_sms': {
                'url': '/api/v1/sms/send',
                'method': 'POST',
                'description': 'Send SMS to single or multiple recipients'
            },
            'send_bulk': {
                'url': '/api/v1/sms/bulk',
                'method': 'POST',
                'description': 'Send bulk SMS with custom messages per recipient'
            },
            'check_balance': {
                'url': '/api/v1/balance',
                'method': 'GET',
                'description': 'Check your SMS credit balance'
            },
            'usage_stats': {
                'url': '/api/v1/stats',
                'method': 'GET',
                'description': 'Get your API usage statistics'
            },
            'configure_webhook': {
                'url': '/api/v1/webhooks/configure',
                'method': 'POST',
                'description': 'Configure webhook for delivery notifications'
            }
        },
        'authentication': 'Include X-API-Key header in all requests',
        'docs': '/api/v1/docs'
    })


@developersmsapi.route('/api/v1/sms/send', methods=['POST'])
@require_api_key
def send_sms():
    """
    Send SMS to one or multiple recipients
    Body: {
        "sender": "YourBrand",
        "recipients": ["233XXXXXXXXX"] or "233XXXXXXXXX",
        "message": "Your message here"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or not all(k in data for k in ['sender', 'recipients', 'message']):
            return jsonify({
                'success': False,
                'error': 'Missing required fields',
                'message': 'Please provide sender, recipients, and message'
            }), 400
        
        sender = data['sender']
        recipients = data['recipients']
        message = data['message']
        
        # Normalize recipients to list
        if isinstance(recipients, str):
            recipients = [recipients]
        
        # Validate recipients
        if not recipients or not isinstance(recipients, list):
            return jsonify({
                'success': False,
                'error': 'Invalid recipients',
                'message': 'Recipients must be a phone number or list of phone numbers'
            }), 400
        
        # Prepare Arkesel API request
        arkesel_data = {
            'sender': sender,
            'message': message,
            'recipients': recipients
        }
        
        headers = {
            'api-key': ARKESEL_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Send to Arkesel
        response = requests.post(
            f'{ARKESEL_BASE_URL}/send',
            json=arkesel_data,
            headers=headers
        )
        
        arkesel_response = response.json()
        
        # Return formatted response
        if response.status_code == 200:
            message_id = arkesel_response.get('data', {}).get('id')
            
            # Track message for webhook callbacks
            if message_id:
                api_key = request.headers.get('X-API-Key')
                message_tracking[message_id] = {
                    'api_key': api_key,
                    'sender': sender,
                    'recipients': recipients,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Trigger 'sent' webhook
                trigger_webhook_async(api_key, 'sent', {
                    'message_id': message_id,
                    'sender': sender,
                    'recipients': recipients,
                    'recipients_count': len(recipients)
                })
        
        return jsonify({
            'success': response.status_code == 200,
            'data': {
                'message_id': arkesel_response.get('data', {}).get('id'),
                'recipients_count': len(recipients),
                'status': arkesel_response.get('message', 'SMS sent successfully')
            },
            'raw_response': arkesel_response
        }), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': 'Arkesel API error',
            'message': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@developersmsapi.route('/api/v1/sms/bulk', methods=['POST'])
@require_api_key
def send_bulk_sms():
    """
    Send personalized SMS to multiple recipients
    Body: {
        "sender": "YourBrand",
        "messages": [
            {"recipient": "233XXXXXXXXX", "message": "Hello John"},
            {"recipient": "233YYYYYYYYY", "message": "Hello Jane"}
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'sender' not in data or 'messages' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields',
                'message': 'Please provide sender and messages array'
            }), 400
        
        sender = data['sender']
        messages = data['messages']
        
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({
                'success': False,
                'error': 'Invalid messages',
                'message': 'Messages must be a non-empty array'
            }), 400
        
        results = []
        success_count = 0
        failed_count = 0
        
        # Send each message individually
        for msg in messages:
            if 'recipient' not in msg or 'message' not in msg:
                failed_count += 1
                results.append({
                    'recipient': msg.get('recipient', 'unknown'),
                    'success': False,
                    'error': 'Missing recipient or message'
                })
                continue
            
            try:
                arkesel_data = {
                    'sender': sender,
                    'message': msg['message'],
                    'recipients': [msg['recipient']]
                }
                
                headers = {
                    'api-key': ARKESEL_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    f'{ARKESEL_BASE_URL}/send',
                    json=arkesel_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_count += 1
                    msg_id = response.json().get('data', {}).get('id')
                    results.append({
                        'recipient': msg['recipient'],
                        'success': True,
                        'message_id': msg_id
                    })
                    
                    # Track and trigger webhook
                    if msg_id:
                        api_key = request.headers.get('X-API-Key')
                        message_tracking[msg_id] = {
                            'api_key': api_key,
                            'sender': sender,
                            'recipient': msg['recipient'],
                            'timestamp': datetime.now().isoformat()
                        }
                        trigger_webhook_async(api_key, 'sent', {
                            'message_id': msg_id,
                            'sender': sender,
                            'recipient': msg['recipient']
                        })
                else:
                    failed_count += 1
                    results.append({
                        'recipient': msg['recipient'],
                        'success': False,
                        'error': response.json().get('message', 'Unknown error')
                    })
                    
            except Exception as e:
                failed_count += 1
                results.append({
                    'recipient': msg['recipient'],
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': success_count > 0,
            'summary': {
                'total': len(messages),
                'success': success_count,
                'failed': failed_count
            },
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@developersmsapi.route('/api/v1/balance', methods=['GET'])
@require_api_key
def check_balance():
    """Check SMS credit balance"""
    try:
        headers = {
            'api-key': ARKESEL_API_KEY
        }
        
        response = requests.get(
            'https://sms.arkesel.com/api/v2/clients/balance-details',
            headers=headers
        )
        
        balance_data = response.json()
        
        return jsonify({
            'success': response.status_code == 200,
            'balance': balance_data.get('data', {})
        }), response.status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch balance',
            'message': str(e)
        }), 500


@developersmsapi.route('/api/v1/stats', methods=['GET'])
@require_api_key
def usage_stats():
    """Get client usage statistics"""
    api_key = request.headers.get('X-API-Key')
    client = api_keys[api_key]
    
    return jsonify({
        'success': True,
        'stats': {
            'client_name': client['name'],
            'tier': client['tier'],
            'total_requests': client['total_requests'],
            'rate_limit': f"{client['rpm_limit']} requests/minute",
            'member_since': client['created_at'],
            'current_minute_usage': len(rate_limit_tracker.get(api_key, [])),
            'webhook_configured': client.get('webhook_url') is not None,
            'webhook_deliveries': len(webhook_logs.get(api_key, []))
        }
    })


@developersmsapi.route('/api/v1/webhooks/configure', methods=['POST'])
@require_api_key
def configure_webhook():
    """
    Configure webhook settings for the client
    Body: {
        "webhook_url": "https://your-domain.com/webhook",
        "webhook_secret": "your-secret-key",
        "events": ["sent", "delivered", "failed"]
    }
    """
    try:
        api_key = request.headers.get('X-API-Key')
        data = request.get_json()
        
        if not data or 'webhook_url' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing webhook_url'
            }), 400
        
        webhook_url = data['webhook_url']
        webhook_secret = data.get('webhook_secret', hashlib.sha256(api_key.encode()).hexdigest())
        events = data.get('events', ['sent', 'delivered', 'failed'])
        
        # Validate webhook URL
        if not webhook_url.startswith(('http://', 'https://')):
            return jsonify({
                'success': False,
                'error': 'Invalid webhook URL. Must start with http:// or https://'
            }), 400
        
        # Validate events
        valid_events = ['sent', 'delivered', 'failed', 'expired']
        invalid_events = [e for e in events if e not in valid_events]
        if invalid_events:
            return jsonify({
                'success': False,
                'error': f'Invalid events: {invalid_events}',
                'valid_events': valid_events
            }), 400
        
        # Update client webhook config
        api_keys[api_key]['webhook_url'] = webhook_url
        api_keys[api_key]['webhook_secret'] = webhook_secret
        api_keys[api_key]['webhook_events'] = events
        
        # Test webhook
        test_payload = {
            'event': 'webhook.test',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'message': 'This is a test webhook from Bulk SMS API',
                'api_key': api_key
            }
        }
        
        test_success = send_webhook(webhook_url, test_payload, webhook_secret, api_key)
        
        return jsonify({
            'success': True,
            'message': 'Webhook configured successfully',
            'config': {
                'webhook_url': webhook_url,
                'events': events,
                'test_delivery': 'success' if test_success else 'failed'
            },
            'note': 'Test webhook was sent to your endpoint'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to configure webhook',
            'message': str(e)
        }), 500


@developersmsapi.route('/api/v1/webhooks/test', methods=['POST'])
@require_api_key
def test_webhook():
    """Test webhook delivery"""
    api_key = request.headers.get('X-API-Key')
    client = api_keys[api_key]
    
    if not client.get('webhook_url'):
        return jsonify({
            'success': False,
            'error': 'No webhook configured',
            'message': 'Please configure a webhook first using POST /api/v1/webhooks/configure'
        }), 400
    
    test_payload = {
        'event': 'webhook.test',
        'timestamp': datetime.now().isoformat(),
        'data': {
            'message': 'Manual test webhook',
            'triggered_at': datetime.now().isoformat()
        }
    }
    
    success = send_webhook(
        client['webhook_url'],
        test_payload,
        client.get('webhook_secret', ''),
        api_key
    )
    
    return jsonify({
        'success': success,
        'message': 'Test webhook sent' if success else 'Test webhook failed',
        'webhook_url': client['webhook_url']
    }), 200 if success else 500


@developersmsapi.route('/api/v1/webhooks/logs', methods=['GET'])
@require_api_key
def webhook_logs_endpoint():
    """Get webhook delivery logs"""
    api_key = request.headers.get('X-API-Key')
    logs = webhook_logs.get(api_key, [])
    
    # Support pagination
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    
    paginated_logs = logs[offset:offset + limit]
    
    return jsonify({
        'success': True,
        'total': len(logs),
        'limit': limit,
        'offset': offset,
        'logs': paginated_logs
    })


@developersmsapi.route('/api/v1/webhooks/disable', methods=['POST'])
@require_api_key
def disable_webhook():
    """Disable webhook notifications"""
    api_key = request.headers.get('X-API-Key')
    
    api_keys[api_key]['webhook_url'] = None
    api_keys[api_key]['webhook_secret'] = None
    
    return jsonify({
        'success': True,
        'message': 'Webhook disabled successfully'
    })


@developersmsapi.route('/webhooks/arkesel/delivery', methods=['POST'])
def arkesel_webhook_receiver():
    """
    Receive delivery reports from Arkesel and forward to client webhooks
    This endpoint should be configured in your Arkesel dashboard
    """
    try:
        # Verify webhook is from Arkesel (implement based on Arkesel's auth method)
        signature = request.headers.get('X-Arkesel-Signature')
        
        # Parse Arkesel webhook payload
        data = request.get_json()
        
        message_id = data.get('id') or data.get('message_id')
        status = data.get('status', '').lower()
        
        if not message_id or message_id not in message_tracking:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
        
        # Get original message details
        msg_info = message_tracking[message_id]
        api_key = msg_info['api_key']
        
        # Map Arkesel status to our events
        event_mapping = {
            'delivered': 'delivered',
            'sent': 'sent',
            'failed': 'failed',
            'undelivered': 'failed',
            'expired': 'expired'
        }
        
        event_type = event_mapping.get(status, 'unknown')
        
        # Prepare webhook payload for client
        webhook_data = {
            'message_id': message_id,
            'status': status,
            'sender': msg_info.get('sender'),
            'recipient': msg_info.get('recipient') or msg_info.get('recipients'),
            'delivered_at': data.get('delivered_at'),
            'error_message': data.get('error_message'),
            'raw_data': data
        }
        
        # Trigger client webhook
        trigger_webhook_async(api_key, event_type, webhook_data)
        
        return jsonify({'success': True, 'message': 'Webhook processed'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@developersmsapi.route('/api/v1/docs')
def documentation():
    """Detailed API documentation"""
    return jsonify({
        'title': 'Bulk SMS API Documentation',
        'base_url': request.host_url,
        'authentication': {
            'type': 'API Key',
            'header': 'X-API-Key',
            'example': 'X-API-Key: your-api-key-here'
        },
        'endpoints': {
            'send_sms': {
                'url': '/api/v1/sms/send',
                'method': 'POST',
                'description': 'Send SMS to single or multiple recipients with the same message',
                'request_body': {
                    'sender': 'string (max 11 chars)',
                    'recipients': 'string or array of strings',
                    'message': 'string'
                },
                'example': {
                    'sender': 'YourBrand',
                    'recipients': ['233XXXXXXXXX', '233YYYYYYYYY'],
                    'message': 'Hello! This is a test message.'
                }
            },
            'send_bulk': {
                'url': '/api/v1/sms/bulk',
                'method': 'POST',
                'description': 'Send personalized SMS to multiple recipients',
                'request_body': {
                    'sender': 'string',
                    'messages': 'array of {recipient, message} objects'
                },
                'example': {
                    'sender': 'YourBrand',
                    'messages': [
                        {'recipient': '233XXXXXXXXX', 'message': 'Hello John!'},
                        {'recipient': '233YYYYYYYYY', 'message': 'Hello Jane!'}
                    ]
                }
            },
            'webhooks': {
                'configure': {
                    'url': '/api/v1/webhooks/configure',
                    'method': 'POST',
                    'description': 'Configure webhook for delivery notifications',
                    'request_body': {
                        'webhook_url': 'string (your endpoint URL)',
                        'webhook_secret': 'string (optional, auto-generated if not provided)',
                        'events': 'array of event types to subscribe to'
                    },
                    'example': {
                        'webhook_url': 'https://your-domain.com/webhook',
                        'webhook_secret': 'your-secret-key',
                        'events': ['sent', 'delivered', 'failed']
                    }
                },
                'test': {
                    'url': '/api/v1/webhooks/test',
                    'method': 'POST',
                    'description': 'Send a test webhook to verify configuration'
                },
                'logs': {
                    'url': '/api/v1/webhooks/logs',
                    'method': 'GET',
                    'description': 'View webhook delivery logs',
                    'query_params': {
                        'limit': 'number of logs to return (default: 50)',
                        'offset': 'offset for pagination (default: 0)'
                    }
                },
                'disable': {
                    'url': '/api/v1/webhooks/disable',
                    'method': 'POST',
                    'description': 'Disable webhook notifications'
                }
            }
        },
        'webhook_events': {
            'sent': 'SMS was accepted and queued for delivery',
            'delivered': 'SMS was successfully delivered to recipient',
            'failed': 'SMS delivery failed',
            'expired': 'SMS expired before delivery'
        },
        'webhook_payload_format': {
            'event': 'string (event type)',
            'timestamp': 'ISO 8601 timestamp',
            'data': {
                'message_id': 'string',
                'status': 'string',
                'sender': 'string',
                'recipient': 'string or array',
                'delivered_at': 'ISO 8601 timestamp (if delivered)',
                'error_message': 'string (if failed)'
            }
        },
        'webhook_security': {
            'signature_header': 'X-Webhook-Signature',
            'algorithm': 'HMAC-SHA256',
            'verification': 'Calculate HMAC of JSON payload with your webhook_secret and compare with signature'
        },
        'rate_limits': {
            'basic': '10 requests/minute',
            'pro': '100 requests/minute',
            'enterprise': 'Custom'
        },
        'response_format': {
            'success': 'boolean',
            'data': 'object',
            'error': 'string (if failed)'
        }
    })


# Admin endpoint to create new API keys (protect this in production!)
@developersmsapi.route('/admin/create-key', methods=['POST'])
def create_api_key():
    """Create a new API key for a client"""
    data = request.get_json()
    
    if not data or 'client_name' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing client_name'
        }), 400
    
    client_name = data['client_name']
    tier = data.get('tier', 'basic')
    
    # Set rate limits based on tier
    rpm_limits = {
        'basic': 10,
        'pro': 100,
        'enterprise': 1000
    }
    
    new_key = generate_api_key(client_name)
    
    api_keys[new_key] = {
        'name': client_name,
        'tier': tier,
        'rpm_limit': rpm_limits.get(tier, 10),
        'total_requests': 0,
        'created_at': datetime.now().isoformat(),
        'webhook_url': None,
        'webhook_secret': None,
        'webhook_events': ['sent', 'delivered', 'failed']
    }
    
    return jsonify({
        'success': True,
        'api_key': new_key,
        'client': api_keys[new_key]
    }), 201
