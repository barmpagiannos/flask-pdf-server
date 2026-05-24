from flask import Flask, render_template, request, send_from_directory, redirect, url_for, abort
import os
import socket
from werkzeug.utils import secure_filename
from zeroconf import ServiceInfo, Zeroconf

app = Flask(__name__)

PDF_FOLDER = "my_pdfs"
app.config['UPLOAD_FOLDER'] = PDF_FOLDER

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

# ----------------- API ENDPOINTS -----------------

@app.route('/')
def home():
    files = [f for f in os.listdir(PDF_FOLDER) if f.endswith('.pdf')]
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "File not found", 400
    
    file = request.files['file']
    
    if file.filename == '':
        return "No file selected", 400
    
    if file and file.filename.lower().endswith('.pdf'):
        original_name = file.filename
        base_name, extension = os.path.splitext(original_name)
        clean_base = secure_filename(base_name)
        
        if not clean_base:
            clean_base = "pdf_file"
            
        final_filename = f"{clean_base}{extension.lower()}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], final_filename))
        return redirect(url_for('home'))
    
    return "Only PDF files are allowed!", 400

@app.route('/delete/<pdf_name>', methods=['POST'])
def delete_file(pdf_name):
    filename = f"{pdf_name}.pdf"
    file_path = os.path.abspath(os.path.join(PDF_FOLDER, filename))
    safe_folder = os.path.abspath(PDF_FOLDER)
    
    if not file_path.startswith(safe_folder):
        abort(403, description="Path Traversal Detected")

    if os.path.exists(file_path):
        os.remove(file_path)
        return redirect(url_for('home'))
    else:
        abort(404, description="File not found.")

@app.route('/<pdf_name>')
def get_pdf(pdf_name):
    filename = f"{pdf_name}.pdf"
    if os.path.exists(os.path.join(PDF_FOLDER, filename)):
        return send_from_directory(PDF_FOLDER, filename)
    abort(404)

# ----------------- Start SERVER & mDNS -----------------

if __name__ == '__main__':
    # 1. Find local IP address.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    # 2. Hostname and Domain (Attention: Remove spaces and use .local)
    # my_hostname = socket.gethostname().lower().replace(" ", "-").
    
    my_hostname = "" ### Add your local hostname here!
    domain_name = f"{my_hostname}.local"

    # 3. Zeroconf settings (now HTTP, not HTTPS).
    desc = {'path': '/'}
    info = ServiceInfo(
        "_http._tcp.local.",
        f"{my_hostname}._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=5000,
        properties=desc,
        server=f"{domain_name}.",
    )

    zeroconf = Zeroconf()
    
    # These MUST be printed now in your terminal!
    print("\n" + "="*50)
    print(f"[*] Server is starting!")
    print(f"[*] You can access it from your mobile device at: http://{domain_name}:5000")
    print(f"[*] Or alternatively with the IP: http://{local_ip}:5000")
    print("="*50 + "\n")
    
    zeroconf.register_service(info)

    try:
        # We removed ssl_context='adhoc' to run in plain HTTP.
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        print("\n[*] Stopping the mDNS announcement...")
        zeroconf.unregister_service(info)
        zeroconf.close()