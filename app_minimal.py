#!/usr/bin/env python3
"""Minimal working dashboard for testing"""

from flask import Flask, render_template_string, request, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

DATABASE = "/tmp/support.db"

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY,
            sender_email TEXT,
            sender_name TEXT, 
            subject TEXT,
            body TEXT,
            classification TEXT,
            draft_text TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # Add test data
    test_data = [
        ("john@example.com", "John Smith", "Account Access Issue", "I can't access my account", "general_inquiry", "Hi John, please try resetting your password..."),
        ("sarah@example.com", "Sarah Johnson", "Refund Request", "Need a refund for my purchase", "billing", "Hi Sarah, I'll process your refund request..."),
    ]
    
    for email, name, subject, body, classification, draft in test_data:
        db.execute("INSERT OR IGNORE INTO drafts (sender_email, sender_name, subject, body, classification, draft_text) VALUES (?,?,?,?,?,?)",
                  (email, name, subject, body, classification, draft))
    
    db.commit()
    db.close()

@app.route('/')
def dashboard():
    db = get_db()
    drafts = db.execute("SELECT * FROM drafts WHERE status='pending'").fetchall()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ennie Support Dashboard</title>
        <style>
            body { font-family: -apple-system, sans-serif; margin: 40px; background: #f5f5f5; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .btn { padding: 8px 16px; margin: 5px; border-radius: 6px; border: none; cursor: pointer; }
            .btn-approve { background: #34c759; color: white; }
            .btn-reject { background: #ff3b30; color: white; }
            h1 { color: #1d1d1f; }
            .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .status-pending { background: #fff3cd; color: #856404; }
        </style>
    </head>
    <body>
        <h1>📧 Support Dashboard</h1>
        <p>{{ drafts|length }} pending drafts</p>
        
        {% for draft in drafts %}
        <div class="card">
            <h3>{{ draft.sender_name }} &lt;{{ draft.sender_email }}&gt;</h3>
            <p><strong>Subject:</strong> {{ draft.subject }}</p>
            <p><strong>Message:</strong> {{ draft.body }}</p>
            <p><strong>Classification:</strong> {{ draft.classification }}</p>
            <div style="background: #f8f9fa; padding: 10px; border-radius: 6px; margin: 10px 0;">
                <strong>Draft Reply:</strong><br>
                {{ draft.draft_text }}
            </div>
            <span class="status status-pending">{{ draft.status.upper() }}</span>
            <div style="margin-top: 15px;">
                <button class="btn btn-approve" onclick="approve({{ draft.id }})">✓ Approve</button>
                <button class="btn btn-reject" onclick="reject({{ draft.id }})">✗ Reject</button>
            </div>
        </div>
        {% endfor %}
        
        <script>
        function approve(id) {
            fetch('/approve/' + id, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.ok) location.reload();
                else alert('Error: ' + data.error);
            });
        }
        
        function reject(id) {
            fetch('/reject/' + id, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.ok) location.reload(); 
                else alert('Error: ' + data.error);
            });
        }
        </script>
    </body>
    </html>
    ''', drafts=drafts)

@app.route('/approve/<int:draft_id>', methods=['POST'])
def approve(draft_id):
    db = get_db()
    db.execute("UPDATE drafts SET status='approved' WHERE id=?", (draft_id,))
    db.commit()
    return jsonify({"ok": True})

@app.route('/reject/<int:draft_id>', methods=['POST'])  
def reject(draft_id):
    db = get_db()
    db.execute("UPDATE drafts SET status='rejected' WHERE id=?", (draft_id,))
    db.commit()
    return jsonify({"ok": True})

@app.route('/reset')
def reset():
    init_db()
    return "Database reset with test data. <a href='/'>Go to dashboard</a>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))