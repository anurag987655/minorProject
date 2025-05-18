from flask import Flask, request, send_file, render_template
import time
import os
import re
from werkzeug.utils import secure_filename
from datetime import datetime
import shutil
import requests
from recognizer import recognize_face


TELEGRAM_BOT_TOKEN = "7804622358:AAHV9cTE63_si10Q_GQX2a4Imb9RFO88dCE"
TELEGRAM_CHAT_ID = "7246953653"

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB limit
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
MAX_IMAGES = 20  # Limit to 20 images

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.after_request
def add_header(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
@app.template_filter('timestamp_to_date')
def timestamp_to_date_filter(ts):
    """
    Strip out all non‐digit characters from ts, 
    parse the remaining as an int Unix timestamp, 
    and format it.
    """
    try:
        # remove everything except digits
        digits = re.sub(r'\D', '', ts)
        return datetime.fromtimestamp(int(digits))\
                       .strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return 'Invalid timestamp'
    
    
def send_telegram_alert(filename):
    try:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        identity = recognize_face(image_path)

        timestamp_str = filename.split('_')[1].split('.')[0]
        timestamp = int(timestamp_str)
        date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        if identity == "Unknown":
            alert_type = "🚨 INTRUDER ALERT!"
        elif identity == "No face detected":
            alert_type = "⚠️ No Face Detected"
        else:
            alert_type = f"✅ Owner Detected: {identity}"
        


        message = (
            f"{alert_type}\n"
            f"Time: {date_str}\n"
            f"Device IP: {request.remote_addr}"
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        requests.post(url, data=data)
    except Exception as e:
        app.logger.error(f"Telegram alert failed: {str(e)}")

    
def enforce_image_limit():
    """Keep only the most recent MAX_IMAGES files, delete the rest."""
    files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith('capture_')]
    files_sorted = sorted(files, key=lambda x: int(x.split('_')[1].split('.')[0]), reverse=True)

    for file_to_delete in files_sorted[MAX_IMAGES:]:
        path_to_delete = os.path.join(app.config['UPLOAD_FOLDER'], file_to_delete)
        try:
            os.remove(path_to_delete)
        except Exception as e:
            app.logger.error(f"Error deleting {file_to_delete}: {str(e)}")

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return 'No image in request', 400
        
    file = request.files['image']
    if file.filename == '':
        return 'Empty filename', 400
        
    if file and allowed_file(file.filename):
        timestamp = str(int(time.time()))
        filename = f"capture_{timestamp}.jpg"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(save_path)
            enforce_image_limit()
            send_telegram_alert(filename)
            return f'Image {filename} saved', 200
        except Exception as e:
            app.logger.error(f"Save error: {str(e)}")
            return 'Server error', 500
            
    return 'Invalid file type', 400

def get_upload_folder_size_mb():
    folder = app.config['UPLOAD_FOLDER']
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return round(total_size / (1024 * 1024), 2)  # Size in MB


@app.route('/')
def index():
    try:
        images = sorted(
            [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.startswith('capture_')],
            key=lambda x: int(x.split('_')[1].split('.')[0]),
            reverse=True
        )
    except Exception as e:
        app.logger.error(f"Sorting error: {str(e)}")
        images = []

    used_mb = get_upload_folder_size_mb()
    total_mb = 20  

    return render_template(
        'index.html',
        images=images,
        used_space=used_mb,
        total_space=total_mb
    )


@app.route('/uploads/<filename>')
def serve_image(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(path):
        return 'File not found', 404
    return send_file(path, mimetype='image/jpeg')

@app.route('/gallery')
def gallery_partial():
    folder = app.config['UPLOAD_FOLDER']
    try:
        files = [
            f for f in os.listdir(folder)
            if f.startswith('capture_') and f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        images = sorted(
            files,
            key=lambda x: int(x.split('_')[1].split('.')[0]),
            reverse=True
        )
    except Exception as e:
        app.logger.error(f"Gallery error: {e}")
        images = []

    return render_template('gallery_partial.html', images=images)





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
