#!/usr/bin/env python3
"""
Simple Working Railway Dashboard 
Minimal Flask app that receives emails from local poller and displays them
"""

from flask import Flask, render_template_string, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DATABASE = "/tmp/support.db"

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT UNIQUE,
            from_email TEXT NOT NULL,
            from_name TEXT,
            subject TEXT NOT NULL,
            body_original TEXT NOT NULL,
            draft_body TEXT,
            classification TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    db.commit()
    db.close()

@app.route('/')
def dashboard():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    try:
        drafts = db.execute("""
            SELECT * FROM drafts 
            WHERE status = 'pending' 
            ORDER BY created_at DESC
        """).fetchall()
    except:
        drafts = []
    finally:
        db.close()
    
    # Calculate stats
    event_count = len([d for d in drafts if 'event' in d.get('classification', '')])
    healing_count = len([d for d in drafts if 'healing' in d.get('classification', '')])
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Ennie Support Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.1); backdrop-filter: blur(20px);
            border-radius: 16px; padding: 24px; margin-bottom: 24px; text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header h1 { color: white; font-size: 28px; margin: 0 0 8px 0; }
        .header p { color: rgba(255,255,255,0.8); margin: 0; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card {
            background: rgba(255,255,255,0.1); backdrop-filter: blur(20px);
            border-radius: 12px; padding: 16px; text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-number { font-size: 24px; font-weight: 700; color: white; margin-bottom: 4px; }
        .stat-label { color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase; }
        .draft-card {
            background: rgba(255,255,255,0.95); border-radius: 16px; padding: 20px;
            margin-bottom: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .draft-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
        .contact h3 { margin: 0 0 4px 0; color: #1a1a1a; font-size: 18px; }
        .contact .email { color: #666; font-size: 14px; }
        .tag {
            background: #007AFF; color: white; padding: 4px 10px; border-radius: 12px;
            font-size: 11px; font-weight: 600; text-transform: capitalize;
        }
        .tag:contains("event") { background: #34C759; }
        .tag:contains("healing") { background: #AF52DE; }
        .tag:contains("media") { background: #FF9500; }
        .subject { font-weight: 600; margin-bottom: 10px; color: #333; font-size: 15px; }
        .original, .reply { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; }
        .original { background: #f8f9fa; border-left: 4px solid #007AFF; }
        .reply { background: #e8f5e8; border-left: 4px solid #34C759; }
        .original h4, .reply h4 {
            margin: 0 0 6px 0; font-size: 11px; color: #666;
            text-transform: uppercase; font-weight: 600;
        }
        .reply p { white-space: pre-line; line-height: 1.4; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn {
            padding: 8px 14px; border-radius: 6px; border: none;
            font-weight: 600; color: white; cursor: pointer; font-size: 13px;
        }
        .btn-approve { background: #34C759; }
        .btn-edit { background: #007AFF; }
        .btn-escalate { background: #FF9500; }
        .btn-reject { background: #FF3B30; }
        .live-indicator {
            position: fixed; top: 16px; right: 16px; background: #34C759;
            color: white; padding: 6px 10px; border-radius: 16px; font-size: 11px; font-weight: 600;
        }
        .empty { text-align: center; padding: 40px 20px; color: rgba(255,255,255,0.8); }
        @media (max-width: 768px) {
            .draft-header { flex-direction: column; align-items: flex-start; }
            .actions { width: 100%; } .btn { flex: 1; }
        }
    </style>
</head>
<body>
    <div class="live-indicator">🔴 LIVE</div>
    <div class="container">
        <div class="header">
            <h1>📧 Ennie Support Dashboard</h1>
            <p>Team Access • Auto-updates • {{ drafts|length }} Pending</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ drafts|length }}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ event_count }}</div>
                <div class="stat-label">Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ healing_count }}</div>
                <div class="stat-label">Healing</div>
            </div>
        </div>
        
        {% if drafts %}
            {% for draft in drafts %}
            <div class="draft-card">
                <div class="draft-header">
                    <div class="contact">
                        <h3>{{ draft.from_name or 'Unknown' }}</h3>
                        <div class="email">{{ draft.from_email }}</div>
                    </div>
                    <div class="tag">{{ (draft.classification or 'general').replace('_', ' ') }}</div>
                </div>
                
                <div class="subject">{{ draft.subject }}</div>
                
                <div class="original">
                    <h4>Original Email</h4>
                    <p>{{ draft.body_original }}</p>
                </div>
                
                <div class="reply">
                    <h4>AI Draft Reply</h4>
                    <p>{{ draft.draft_body }}</p>
                </div>
                
                <div class="actions">
                    <button class="btn btn-approve">✓ Approve</button>
                    <button class="btn btn-edit">✎ Edit</button>
                    <button class="btn btn-escalate">⚠ Escalate</button>
                    <button class="btn btn-reject">✗ Reject</button>
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">
                <h2>No Pending Support Emails</h2>
                <p>All caught up! New emails will appear here automatically.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
    ''', drafts=drafts, event_count=event_count, healing_count=healing_count)

@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    """Receive drafts from local poller"""
    try:
        data = request.get_json() or {}
        
        # Required fields
        required = ['thread_id', 'from_email', 'from_name', 'subject', 'body_original', 'draft_body', 'classification']
        if not all(data.get(k) for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        db = sqlite3.connect(DATABASE)
        
        # Insert or update draft
        db.execute("""
            INSERT OR REPLACE INTO drafts 
            (thread_id, from_email, from_name, subject, body_original, draft_body, classification, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
        """, (
            data['thread_id'], data['from_email'], data['from_name'],
            data['subject'], data['body_original'][:1000], data['draft_body'][:1000], 
            data['classification']
        ))
        
        db.commit()
        draft_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.close()
        
        return jsonify({'ok': True, 'draft_id': draft_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset')
def reset():
    """Reset database - for testing"""
    init_db()
    return 'Database reset. <a href="/">View Dashboard</a>'

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))