from flask import Flask, request, jsonify, render_template_string
import requests
import time
import logging
import hashlib
import os
import re
from datetime import datetime
from collections import deque
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# ══════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════
# Auto-detect WA_BOT_URL: If local, use 127.0.0.1:5001, otherwise use public URL
WA_BOT_URL = os.environ.get("WA_BOT_URL", "https://sms-tg-production.up.railway.app/send_code")

SMS_FILTER_SENDER = os.environ.get("SMS_FILTER_SENDER", "3737")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Memory storage for the Dashboard (last 20 messages)
history = deque(maxlen=20)
recent_hashes = {}

# ══════════════════════════════════════════
#  DASHBOARD TEMPLATE
# ══════════════════════════════════════════
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Skyline Bridge Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f7f6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
        .status-success { background: #d4edda; color: #155724; }
        .status-ignored { background: #fff3cd; color: #856404; }
        .status-error { background: #f8d7da; color: #721c24; }
        .status-duplicate { background: #e2e3e5; color: #383d41; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: #666; }
        pre { background: #f1f1f1; padding: 5px; border-radius: 4px; font-size: 11px; white-space: pre-wrap; max-width: 300px; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; text-decoration: none; font-size: 14px; }
        .refresh-btn:hover { background: #2980b9; }
        .code-highlight { color: #e74c3c; font-weight: bold; font-family: monospace; font-size: 1.1em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🚀 Skyline Bridge Logs</span>
            <a href="/" class="refresh-btn">🔄 Refresh Dashboard</a>
        </h1>
        <p><strong>Configured Sender:</strong> <code style="background:#eee;padding:2px 5px">{{ filter_sender }}</code> | <strong>WA Bot:</strong> <code>{{ wa_url }}</code></p>
        
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>From</th>
                    <th>Message / Code</th>
                    <th>Status</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {% for item in history %}
                <tr>
                    <td>{{ item.time }}</td>
                    <td><strong>{{ item.sender }}</strong></td>
                    <td>
                        <div>{{ item.content }}</div>
                        {% if item.code %}<div class="code-highlight">OTP: {{ item.code }}</div>{% endif %}
                    </td>
                    <td><span class="status-badge status-{{ item.status_class }}">{{ item.status }}</span></td>
                    <td><pre>{{ item.debug }}</pre></td>
                </tr>
                {% else %}
                <tr><td colspan="5" style="text-align:center;padding:40px;color:#999;">No messages received yet. Send an SMS to your modem!</td></tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div style="margin-top:30px; padding:15px; background:#e8f4fd; border-radius:8px; border-left:5px solid #3498db;">
            <strong>💡 Testing Tip:</strong> To test the bridge without a modem, call: <br>
            <code>/test</code> (Direct to WA) or use Postman to send a POST to <code>/sms</code>.
        </div>
    </div>
</body>
</html>
"""

# ══════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════
def is_duplicate(sender, content):
    msg_hash = hashlib.md5(f"{sender}{content}".encode()).hexdigest()
    current_time = time.time()
    if msg_hash in recent_hashes:
        if current_time - recent_hashes[msg_hash] < 45: # 45 second duplicate window
            return True
    recent_hashes[msg_hash] = current_time
    return False

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        requests.post(TELEGRAM_API, data={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=5)
    except: pass

# ══════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════

@app.route('/', methods=['GET'])
def dashboard():
    return render_template_string(
        DASHBOARD_HTML, 
        history=reversed(list(history)), 
        filter_sender=SMS_FILTER_SENDER,
        wa_url=WA_BOT_URL
    )

@app.route('/sms', methods=['POST', 'GET'])
def receive_sms():
    log_entry = {
        "time": datetime.now().strftime('%H:%M:%S'),
        "sender": "Unknown",
        "content": "",
        "code": None,
        "status": "Processing",
        "status_class": "ignored",
        "debug": ""
    }
    
    try:
        # Extract metadata from all possible sources (URL args, Form, JSON)
        args = dict(request.args)
        form = dict(request.form)
        json_data = request.get_json(silent=True) or {}
        raw_body = request.get_data(as_text=True)
        
        log_entry["debug"] = f"Args: {args}\nForm: {form}\nBody: {raw_body[:100]}"
        
        sender = args.get('sender') or form.get('sender') or json_data.get('sender') or 'Unknown'
        receiver = args.get('receiver') or form.get('receiver') or 'Unknown'
        log_entry["sender"] = sender

        # Content extraction
        content = args.get('message') or form.get('message') or json_data.get('message') or \
                  args.get('content') or form.get('content') or ""
        
        if not content and raw_body:
            # Try parsing raw formats often used by modems
            if '\n\n' in raw_body:
                content = raw_body.split('\n\n')[1].strip()
            else:
                content = raw_body.strip()

        log_entry["content"] = content

        # ── 1. VALIDATION ──
        if not content:
            log_entry["status"] = "EMTPY"
            history.append(log_entry)
            return jsonify({"status": "empty"}), 200

        # ── 2. FILTER SENDER ──
        if SMS_FILTER_SENDER and sender != SMS_FILTER_SENDER:
            log_entry["status"] = f"IGNORED"
            log_entry["debug"] += f"\nFilter: {SMS_FILTER_SENDER} != {sender}"
            history.append(log_entry)
            return jsonify({"status": "ignored"}), 200

        # ── 3. DUPLICATE CHECK ──
        if is_duplicate(sender, content):
            log_entry["status"] = "DUPLICATE"
            log_entry["status_class"] = "duplicate"
            history.append(log_entry)
            return jsonify({"status": "duplicate"}), 200

        # ── 4. EXTRACT CODE ──
        # Looks for 4-8 digit codes (inclusive)
        code_match = re.search(r'\b(\d{4,8})\b', content)
        if code_match:
            code = code_match.group(1)
            log_entry["code"] = code
            
            # ── 5. FORWARD TO WHATSAPP ──
            try:
                wa_resp = requests.post(
                    WA_BOT_URL, 
                    json={"code": code, "message": content, "sender": sender}, 
                    timeout=10
                )
                if wa_resp.status_code == 200:
                    log_entry["status"] = "SENT ✅"
                    log_entry["status_class"] = "success"
                else:
                    log_entry["status"] = f"WA ERR {wa_resp.status_code}"
                    log_entry["status_class"] = "error"
            except Exception as e:
                log_entry["status"] = "WA BOT OFFLINE"
                log_entry["status_class"] = "error"
                log_entry["debug"] += f"\nWA Error: {str(e)}"
        else:
            log_entry["status"] = "NO CODE FOUND"
            log_entry["debug"] += "\nRegex for 4-8 digits failed."

        # ── 6. TELEGRAM NOTIFY ──
        tg_msg = f"📩 <b>SMS:</b> {sender}\n💬 {content}"
        if log_entry["code"]: tg_msg += f"\n🎯 <b>CODE:</b> <code>{log_entry['code']}</code>"
        send_telegram(tg_msg)

        history.append(log_entry)
        return jsonify({"status": "processed", "code": log_entry["code"]}), 200

    except Exception as e:
        logger.error(f"Error: {e}")
        log_entry["status"] = "CRASH"
        log_entry["status_class"] = "error"
        log_entry["debug"] += f"\nCrash: {str(e)}"
        history.append(log_entry)
        return jsonify({"status": "error"}), 500

@app.route('/test', methods=['GET'])
def test():
    """Simple test route to verify WA bot connectivity"""
    try:
        wa_resp = requests.post(WA_BOT_URL, json={"code": "123456", "message": "TEST FROM DASHBOARD"}, timeout=5)
        return f"Test sent to WA. Response: {wa_resp.text}", 200
    except Exception as e:
        return f"WA Bot connection failed: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
