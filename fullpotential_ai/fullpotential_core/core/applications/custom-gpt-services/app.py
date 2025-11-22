#!/usr/bin/env python3
"""
Custom GPT Services - Simple Flask Backend
Handles inquiry forms and consultation bookings
"""

from flask import Flask, request, render_template_string, jsonify
import os
from datetime import datetime
import json

app = Flask(__name__)

# Store inquiries in JSON file (in production, use a database)
INQUIRIES_FILE = 'inquiries.json'

@app.route('/')
def index():
    """Serve the landing page"""
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/submit-inquiry', methods=['POST'])
def submit_inquiry():
    """Handle consultation inquiry form"""

    inquiry = {
        'timestamp': datetime.now().isoformat(),
        'name': request.form.get('name'),
        'email': request.form.get('email'),
        'company': request.form.get('company', ''),
        'use_case': request.form.get('use_case'),
        'timeline': request.form.get('timeline'),
        'status': 'new'
    }

    # Save inquiry
    inquiries = []
    if os.path.exists(INQUIRIES_FILE):
        with open(INQUIRIES_FILE, 'r') as f:
            inquiries = json.load(f)

    inquiries.append(inquiry)

    with open(INQUIRIES_FILE, 'w') as f:
        json.dump(inquiries, f, indent=2)

    print(f"\n✅ New inquiry from {inquiry['name']} ({inquiry['email']})")
    print(f"   Use case: {inquiry['use_case']}")
    print(f"   Timeline: {inquiry['timeline']}")

    # In production, send email notification here

    return jsonify({
        'success': True,
        'message': 'Thank you! We\'ll contact you within 24 hours to schedule your consultation.'
    })

@app.route('/admin/inquiries')
def view_inquiries():
    """View all inquiries (admin only - add auth in production)"""

    if not os.path.exists(INQUIRIES_FILE):
        return jsonify([])

    with open(INQUIRIES_FILE, 'r') as f:
        inquiries = json.load(f)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Custom GPT Inquiries</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .inquiry { border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
            .inquiry.new { background: #fff3cd; }
            h2 { color: #0f3460; }
            .timestamp { color: #666; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>Custom GPT Service Inquiries ({{ count }})</h1>
        {% for inquiry in inquiries reversed %}
        <div class="inquiry {{ inquiry.status }}">
            <h2>{{ inquiry.name }} - {{ inquiry.company or 'No company' }}</h2>
            <p class="timestamp">{{ inquiry.timestamp }}</p>
            <p><strong>Email:</strong> {{ inquiry.email }}</p>
            <p><strong>Timeline:</strong> {{ inquiry.timeline }}</p>
            <p><strong>Use Case:</strong><br>{{ inquiry.use_case }}</p>
            <p><strong>Status:</strong> <span style="background: #28a745; color: white; padding: 5px 10px; border-radius: 4px;">{{ inquiry.status }}</span></p>
        </div>
        {% endfor %}
    </body>
    </html>
    """

    return render_template_string(html, inquiries=inquiries, count=len(inquiries))

if __name__ == '__main__':
    print("🚀 Starting Custom GPT Services website...")
    print("📍 Running on http://localhost:5001")
    print("💡 Admin dashboard: http://localhost:5001/admin/inquiries")
    print()
    app.run(debug=True, host='0.0.0.0', port=5001)
