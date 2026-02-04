#!/usr/bin/env python3
"""
QuickDrop - Simple Mac ↔ Android File Transfer
Run this on your Mac, open the URL on your Android phone's browser.
"""

import os
import socket
import qrcode
import io
import base64
from pathlib import Path
from flask import Flask, render_template_string, request, send_from_directory, jsonify, Response
from werkzeug.utils import secure_filename

# Configuration
SHARE_FOLDER = os.path.expanduser("~/Downloads/PhoneTransfer")
PORT = 5000

# Create share folder if it doesn't exist
os.makedirs(SHARE_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB max upload

def get_local_ip():
    """Get the local IP address of this machine"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def generate_qr_code(url):
    """Generate QR code as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()

def get_file_size_str(size_bytes):
    """Convert bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickDrop</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #888;
            font-size: 0.95rem;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .card h2 {
            font-size: 1.2rem;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .upload-zone {
            border: 2px dashed rgba(0, 217, 255, 0.4);
            border-radius: 12px;
            padding: 50px 20px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .upload-zone:hover, .upload-zone.dragover {
            border-color: #00d9ff;
            background: rgba(0, 217, 255, 0.1);
        }
        
        .upload-zone p {
            color: #aaa;
            margin-top: 10px;
        }
        
        .upload-icon {
            font-size: 3rem;
            margin-bottom: 10px;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .btn {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #000;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 217, 255, 0.4);
        }
        
        .file-list {
            list-style: none;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            margin-bottom: 10px;
            transition: background 0.2s;
        }
        
        .file-item:hover {
            background: rgba(255, 255, 255, 0.08);
        }
        
        .file-info {
            display: flex;
            align-items: center;
            gap: 15px;
            flex: 1;
            min-width: 0;
        }
        
        .file-icon {
            font-size: 1.5rem;
            width: 40px;
            text-align: center;
        }
        
        .file-details {
            flex: 1;
            min-width: 0;
        }
        
        .file-name {
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .file-size {
            color: #888;
            font-size: 0.85rem;
        }
        
        .download-btn {
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
            text-decoration: none;
        }
        
        .download-btn:hover {
            background: rgba(0, 255, 136, 0.3);
        }
        
        .progress-container {
            display: none;
            margin-top: 20px;
        }
        
        .progress-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            width: 0%;
            transition: width 0.3s;
        }
        
        .progress-text {
            text-align: center;
            margin-top: 10px;
            color: #888;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: #00ff88;
            color: #000;
            padding: 15px 30px;
            border-radius: 8px;
            font-weight: 500;
            opacity: 0;
            transition: all 0.3s ease;
            z-index: 1000;
        }
        
        .toast.show {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
        
        @media (max-width: 600px) {
            h1 { font-size: 1.8rem; }
            .card { padding: 15px; }
            .upload-zone { padding: 30px 15px; }
            .file-item { flex-direction: column; gap: 10px; align-items: flex-start; }
            .download-btn { width: 100%; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ QuickDrop</h1>
            <p class="subtitle">Fast file transfer between Mac & Android</p>
        </header>
        
        <div class="card">
            <h2>📤 Upload to Mac</h2>
            <div class="upload-zone" id="uploadZone">
                <div class="upload-icon">📁</div>
                <button class="btn" onclick="document.getElementById('fileInput').click()">Select Files</button>
                <p>or drag and drop files here</p>
            </div>
            <input type="file" id="fileInput" multiple>
            <div class="progress-container" id="progressContainer">
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <p class="progress-text" id="progressText">Uploading...</p>
            </div>
        </div>
        
        <div class="card">
            <h2>📥 Download from Mac</h2>
            <ul class="file-list" id="fileList">
                {% if files %}
                    {% for file in files %}
                    <li class="file-item">
                        <div class="file-info">
                            <span class="file-icon">{{ file.icon }}</span>
                            <div class="file-details">
                                <div class="file-name">{{ file.name }}</div>
                                <div class="file-size">{{ file.size }}</div>
                            </div>
                        </div>
                        <a href="/download/{{ file.name | urlencode }}" class="download-btn">Download</a>
                    </li>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <p>No files in shared folder yet</p>
                        <p style="font-size: 0.85rem; margin-top: 5px;">{{ share_folder }}</p>
                    </div>
                {% endif %}
            </ul>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }
        
        function uploadFiles(files) {
            if (files.length === 0) return;
            
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }
            
            progressContainer.style.display = 'block';
            progressFill.style.width = '0%';
            
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = percent + '%';
                    progressText.textContent = `Uploading... ${percent}%`;
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    showToast('✓ Upload complete!');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showToast('✗ Upload failed');
                }
                progressContainer.style.display = 'none';
            });
            
            xhr.addEventListener('error', () => {
                showToast('✗ Upload failed');
                progressContainer.style.display = 'none';
            });
            
            xhr.open('POST', '/upload');
            xhr.send(formData);
        }
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            uploadFiles(e.target.files);
        });
        
        // Drag and drop
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            uploadFiles(e.dataTransfer.files);
        });
    </script>
</body>
</html>
'''

def get_file_icon(filename):
    """Return emoji icon based on file extension"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    icons = {
        'pdf': '📕',
        'doc': '📘', 'docx': '📘',
        'xls': '📗', 'xlsx': '📗',
        'ppt': '📙', 'pptx': '📙',
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'webp': '🖼️',
        'mp4': '🎬', 'mov': '🎬', 'avi': '🎬', 'mkv': '🎬',
        'mp3': '🎵', 'wav': '🎵', 'flac': '🎵', 'm4a': '🎵',
        'zip': '📦', 'rar': '📦', '7z': '📦', 'tar': '📦', 'gz': '📦',
        'txt': '📄', 'md': '📄',
        'py': '🐍', 'js': '💛', 'html': '🌐', 'css': '🎨',
        'apk': '🤖',
    }
    return icons.get(ext, '📄')

@app.route('/')
def index():
    files = []
    try:
        for f in os.listdir(SHARE_FOLDER):
            filepath = os.path.join(SHARE_FOLDER, f)
            if os.path.isfile(filepath):
                files.append({
                    'name': f,
                    'size': get_file_size_str(os.path.getsize(filepath)),
                    'icon': get_file_icon(f)
                })
    except Exception as e:
        print(f"Error listing files: {e}")
    
    files.sort(key=lambda x: x['name'].lower())
    return render_template_string(HTML_TEMPLATE, files=files, share_folder=SHARE_FOLDER)

@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return jsonify({'error': 'No files'}), 400
    
    files = request.files.getlist('files')
    uploaded = []
    
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            # Handle duplicate names
            filepath = os.path.join(SHARE_FOLDER, filename)
            if os.path.exists(filepath):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(filepath):
                    filename = f"{base}_{counter}{ext}"
                    filepath = os.path.join(SHARE_FOLDER, filename)
                    counter += 1
            
            file.save(filepath)
            uploaded.append(filename)
    
    return jsonify({'uploaded': uploaded})

@app.route('/download/<path:filename>')
def download(filename):
    """Optimized download with chunked streaming and resume support"""
    # URL decode the filename and sanitize path traversal attempts
    from urllib.parse import unquote
    filename = unquote(filename)
    
    # Security: prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    filepath = os.path.join(SHARE_FOLDER, filename)
    
    # Check file exists and is within share folder
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        return "File not found", 404
    
    real_share = os.path.realpath(SHARE_FOLDER)
    real_file = os.path.realpath(filepath)
    if not real_file.startswith(real_share):
        return "Access denied", 403
    
    file_size = os.path.getsize(filepath)
    chunk_size = 1024 * 1024  # 1MB chunks
    
    # Handle range requests (for resume support)
    range_header = request.headers.get('Range')
    start = 0
    end = file_size - 1
    
    if range_header:
        try:
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
        except (ValueError, IndexError):
            pass
    
    content_length = end - start + 1
    
    def generate():
        with open(filepath, 'rb') as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                chunk = f.read(read_size)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
    
    # Encode filename for Content-Disposition header
    from urllib.parse import quote
    encoded_filename = quote(filename)
    
    headers = {
        'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
        'Content-Length': str(content_length),
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    }
    
    status_code = 206 if range_header else 200
    
    return Response(
        generate(),
        status=status_code,
        mimetype='application/octet-stream',
        headers=headers
    )

def print_banner(url, qr_base64):
    """Print startup banner"""
    print("\n" + "="*50)
    print("  ⚡ QuickDrop - File Transfer Server")
    print("="*50)
    print(f"\n  📁 Shared folder: {SHARE_FOLDER}")
    print(f"\n  🌐 Open this URL on your Android phone:")
    print(f"\n     {url}")
    print(f"\n  📱 Or scan the QR code below:\n")
    
    # Generate ASCII QR code for terminal
    qr = qrcode.QRCode(version=1, box_size=1, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    
    print("\n" + "="*50)
    print("  Press Ctrl+C to stop the server")
    print("="*50 + "\n")

if __name__ == '__main__':
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"
    qr_base64 = generate_qr_code(url)
    
    print_banner(url, qr_base64)
    
    # Use Waitress production server (MUCH faster than Flask dev server)
    try:
        from waitress import serve
        print("  🚀 Running with Waitress (production server)")
        print("     Expected speeds: 30-100+ MB/s on 5GHz WiFi\n")
        serve(app, host='0.0.0.0', port=PORT, threads=8, 
              channel_timeout=120, recv_bytes=262144, send_bytes=262144)
    except ImportError:
        print("  ⚠️  Waitress not found, using Flask dev server (slower)")
        print("     Install waitress for faster transfers: pip3 install waitress\n")
        app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)