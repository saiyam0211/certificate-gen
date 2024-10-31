from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import qrcode
import uuid
import os
import json
from datetime import datetime

app = Flask(__name__)

# Use environment variable for the domain
DOMAIN = os.environ.get('DOMAIN', 'http://localhost:10000')

# Use a directory that Render can write to
UPLOAD_FOLDER = '/tmp/certificates'
DB_PATH = '/tmp/certificates.json'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database functions
def load_database():
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_database(db):
    with open(DB_PATH, 'w') as f:
        json.dump(db, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_certificate():
    recipient = request.form['recipient']
    competition = request.form['competition']
    position = request.form['position']
    
    certificate_id = str(uuid.uuid4())
    verification_code = str(uuid.uuid4())[:8].upper()
    
    certificate_data = {
        "recipient": recipient,
        "competition": competition,
        "position": position,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "certificate_id": certificate_id,
        "verification_code": verification_code
    }
    
    db = load_database()
    db[certificate_id] = certificate_data
    save_database(db)
    
    img = Image.new('RGB', (1500, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    font = ImageFont.load_default()
    
    draw.text((750, 200), "Certificate of Achievement", font=font, anchor="mm")
    draw.text((750, 300), f"This is to certify that", font=font, anchor="mm")
    draw.text((750, 400), recipient, font=font, anchor="mm")
    draw.text((750, 500), f"has achieved {position} place in", font=font, anchor="mm")
    draw.text((750, 600), competition, font=font, anchor="mm")
    draw.text((750, 700), f"Date: {certificate_data['date']}", font=font, anchor="mm")
    
    verification_text = f"""
    To verify this certificate:
    1. Visit: {DOMAIN}/verify
    2. Certificate ID: {certificate_id}
    3. Verification Code: {verification_code}
    """
    draw.text((100, 850), verification_text, font=font)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    verification_url = f"{DOMAIN}/verify/{certificate_id}?code={verification_code}"
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_img.resize((150, 150))
    
    if qr_img.mode != 'RGB':
        qr_img = qr_img.convert('RGB')
    
    img.paste(qr_img, (1250, 750))
    
    certificate_path = os.path.join(UPLOAD_FOLDER, f"{certificate_id}.png")
    img.save(certificate_path)
    
    return send_file(certificate_path, as_attachment=True)

@app.route('/verify', methods=['GET'])
def verify_form():
    return render_template('verify_form.html')

@app.route('/verify/<certificate_id>')
def verify_certificate(certificate_id):
    code = request.args.get('code', '')
    db = load_database()
    certificate_data = db.get(certificate_id)
    
    if not certificate_data:
        return render_template('verify.html', valid=False, error="Certificate not found")
    
    if code != certificate_data.get('verification_code'):
        return render_template('verify.html', valid=False, error="Invalid verification code")
    
    return render_template('verify.html', valid=True, certificate=certificate_data)

@app.route('/api/verify', methods=['POST'])
def verify_api():
    data = request.get_json()
    certificate_id = data.get('certificate_id')
    verification_code = data.get('verification_code')
    
    db = load_database()
    certificate_data = db.get(certificate_id)
    
    if not certificate_data:
        return jsonify({"valid": False, "error": "Certificate not found"})
    
    if verification_code != certificate_data.get('verification_code'):
        return jsonify({"valid": False, "error": "Invalid verification code"})
    
    return jsonify({
        "valid": True,
        "certificate": certificate_data
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)