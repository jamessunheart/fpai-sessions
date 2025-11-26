from flask import Flask, request, render_template_string
import subprocess
import os

app = Flask(__name__)
HTPASSWD_FILE = "/etc/nginx/.htpasswd"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Full Potential Admin Setup</title>
    <style>
        body { font-family: system-ui; background: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h1 { color: #333; margin-top: 0; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        button:hover { background: #5a67d8; }
        .alert { padding: 10px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
        .success { background: #d1fae5; color: #065f46; }
        .error { background: #fee2e2; color: #991b1b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🛡️ Admin Setup</h1>
        
        {% if message %}
            <div class="alert {{ status }}">{{ message }}</div>
        {% endif %}

        {% if not password_set %}
            <p>Set the master password for all <strong>/dashboards/*</strong> routes.</p>
            <form method="POST">
                <input type="text" name="username" value="admin" readonly style="background: #f9fafb; color: #666;">
                <input type="password" name="password" placeholder="New Password" required minlength="8">
                <button type="submit">Set Admin Password</button>
            </form>
        {% else %}
            <p>✅ Admin password is set.</p>
            <p>You can now access protected areas.</p>
            <a href="/dashboards"><button>Go to Dashboards</button></a>
        {% endif %}
    </div>
</body>
</html>
"""

def is_password_set():
    return os.path.exists(HTPASSWD_FILE) and os.path.getsize(HTPASSWD_FILE) > 0

@app.route('/', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        # Verify this is the initial setup or we are overwriting
        # In production, we might want to require the old password to change it
        password = request.form.get('password')
        username = "admin"
        
        if len(password) < 8:
            return render_template_string(HTML_TEMPLATE, message="Password must be at least 8 characters.", status="error", password_set=is_password_set())

        try:
            # Use htpasswd to create/update the file
            # -b = batch mode (read password from command line)
            # -c = create new file (overwrite)
            cmd = ["htpasswd", "-b", "-c", HTPASSWD_FILE, username, password]
            subprocess.run(cmd, check=True)
            
            # Reload nginx to apply changes immediately
            subprocess.run(["systemctl", "reload", "nginx"], check=True)
            
            return render_template_string(HTML_TEMPLATE, message="Password set successfully! Nginx updated.", status="success", password_set=True)
        except Exception as e:
            return render_template_string(HTML_TEMPLATE, message=f"Error setting password: {str(e)}", status="error", password_set=is_password_set())

    return render_template_string(HTML_TEMPLATE, message=None, password_set=is_password_set())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)

