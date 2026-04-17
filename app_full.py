#!/usr/bin/env python3
"""
Ennie Support Dashboard
Real-time dashboard for support email drafts with approval workflow
"""

from flask import Flask, render_template_string, request, jsonify
import json
import os
import sqlite3
from datetime import datetime
import uuid

app = Flask(__name__)

# Debug logging
app.logger.info(f"Starting Ennie Dashboard, DATABASE={DATABASE}")
print(f"[STARTUP] Database path: {DATABASE}")
print(f"[STARTUP] Environment PORT: {os.environ.get('PORT', 'not set')}")
print(f"[STARTUP] Flask app created, registering routes...")

# Database setup
DATABASE = os.environ.get('DATABASE_PATH', '/tmp/ennie_drafts.db')

# Ensure database directory exists
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            message_id TEXT,
            from_email TEXT NOT NULL,
            from_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_original TEXT NOT NULL,
            draft_body TEXT NOT NULL,
            classification TEXT,
            status TEXT DEFAULT 'pending',
            escalate INTEGER DEFAULT 0,
            escalation_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT,
            added_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database on startup
init_db()

@app.route('/test')
def test():
    """Simple test route."""
    return {'status': 'ok', 'message': 'API routes are working'}

@app.route('/api/test')
def api_test():
    """API test route."""
    return jsonify({'api_status': 'working', 'database': DATABASE})

@app.route('/')
def dashboard():
    """Main dashboard view."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get pending drafts
    cursor.execute("""
        SELECT * FROM drafts 
        WHERE status = 'pending' 
        ORDER BY created_at DESC
    """)
    drafts = [dict(row) for row in cursor.fetchall()]
    
    # Calculate stats
    cursor.execute("SELECT COUNT(*) as count FROM drafts WHERE status = 'pending'")
    pending_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM drafts WHERE status = 'approved'")
    approved_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM drafts WHERE escalate = 1 AND status = 'pending'")
    escalated_count = cursor.fetchone()['count']
    
    conn.close()
    
    return render_template_string(DASHBOARD_TEMPLATE, 
                                drafts=drafts, 
                                pending_count=pending_count,
                                approved_count=approved_count,
                                escalated_count=escalated_count)

@app.route('/api/drafts', methods=['POST'])
def create_draft():
    """API endpoint for support runner to submit new drafts."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['from_email', 'from_name', 'subject', 'body_original', 'draft_body']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Generate unique ID
        draft_id = str(uuid.uuid4())
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO drafts (
                id, thread_id, message_id, from_email, from_name, 
                subject, body_original, draft_body, classification, 
                escalate, escalation_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            draft_id,
            data.get('thread_id'),
            data.get('message_id'),
            data['from_email'],
            data['from_name'],
            data['subject'],
            data['body_original'],
            data['draft_body'],
            data.get('classification'),
            1 if data.get('escalate') else 0,
            data.get('escalation_reason')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'id': draft_id, 'status': 'created'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    """API endpoint to fetch drafts."""
    status = request.args.get('status', 'pending')
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM drafts 
        WHERE status = ? 
        ORDER BY created_at DESC
    """, (status,))
    
    drafts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(drafts)

@app.route('/api/drafts/<draft_id>/approve', methods=['POST'])
def approve_draft(draft_id):
    """Approve a draft and mark it as ready to send."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE drafts 
        SET status = 'approved', updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (draft_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Draft not found'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'approved'})

@app.route('/api/drafts/<draft_id>/reject', methods=['POST'])
def reject_draft(draft_id):
    """Reject a draft."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE drafts 
        SET status = 'rejected', updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (draft_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Draft not found'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'rejected'})

@app.route('/api/drafts/<draft_id>/edit', methods=['POST'])
def edit_draft(draft_id):
    """Edit a draft's reply text."""
    data = request.get_json()
    new_body = data.get('draft_body')
    
    if not new_body:
        return jsonify({'error': 'Missing draft_body'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE drafts 
        SET draft_body = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (new_body, draft_id))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Draft not found'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'updated'})

@app.route('/api/knowledge', methods=['POST'])
def add_knowledge():
    """Add new knowledge base entry."""
    data = request.get_json()
    
    if not data.get('question') or not data.get('answer'):
        return jsonify({'error': 'Missing question or answer'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO knowledge_base (question, answer, category, added_by)
        VALUES (?, ?, ?, ?)
    """, (
        data['question'],
        data['answer'],
        data.get('category'),
        data.get('added_by', 'system')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'added'})

@app.route('/api/knowledge', methods=['GET'])
def get_knowledge():
    """Get knowledge base entries."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM knowledge_base 
        ORDER BY created_at DESC
    """)
    
    knowledge = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(knowledge)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# HTML Template for the dashboard
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Ennie Support Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh; padding: 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.1); backdrop-filter: blur(20px);
            border-radius: 16px; padding: 24px; margin-bottom: 24px; text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header h1 { color: #1a1a1a; font-size: 28px; margin: 0 0 8px 0; font-weight: 600; }
        .header p { color: #666; margin: 0; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card {
            background: rgba(255,255,255,0.1); backdrop-filter: blur(20px);
            border-radius: 12px; padding: 16px; text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-number { font-size: 24px; font-weight: 700; color: #1a1a1a; margin-bottom: 4px; }
        .stat-label { color: #666; font-size: 12px; text-transform: uppercase; font-weight: 500; }
        .draft-card {
            background: rgba(255,255,255,0.95); border-radius: 16px; padding: 20px;
            margin-bottom: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.3);
        }
        .draft-card.escalated {
            border-left: 4px solid #FF9500;
            background: rgba(255, 149, 0, 0.05);
        }
        .draft-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
        .contact h3 { margin: 0 0 4px 0; color: #1a1a1a; font-size: 18px; font-weight: 600; }
        .contact .email { color: #666; font-size: 14px; }
        .contact .time { color: #999; font-size: 12px; margin-top: 2px; }
        .tag {
            background: #007AFF; color: white; padding: 4px 10px; border-radius: 12px;
            font-size: 11px; font-weight: 600; text-transform: capitalize;
        }
        .tag.event_question, .tag.event_booking_issue { background: #34C759; }
        .tag.recording_access { background: #AF52DE; }
        .tag.escalated { background: #FF9500; }
        .subject { font-weight: 600; margin-bottom: 10px; color: #333; font-size: 15px; }
        .original, .reply { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; line-height: 1.5; }
        .original { background: #f8f9fa; border-left: 4px solid #007AFF; }
        .reply { background: #e8f5e8; border-left: 4px solid #34C759; }
        .original h4, .reply h4 {
            margin: 0 0 6px 0; font-size: 11px; color: #666;
            text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;
        }
        .reply p { white-space: pre-line; line-height: 1.4; color: #2d5a2d; }
        .escalation-reason {
            background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px;
            padding: 10px; margin-bottom: 12px; color: #856404; font-size: 13px;
        }
        .escalation-reason h4 { margin-bottom: 4px; color: #FF9500; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn {
            padding: 8px 14px; border-radius: 6px; border: none;
            font-weight: 600; color: white; cursor: pointer; font-size: 13px;
            transition: all 0.2s;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .btn-approve { background: #34C759; }
        .btn-edit { background: #007AFF; }
        .btn-escalate { background: #FF9500; }
        .btn-reject { background: #FF3B30; }
        .live-indicator {
            position: fixed; top: 16px; right: 16px; background: #34C759;
            color: white; padding: 6px 10px; border-radius: 16px; font-size: 11px; font-weight: 600;
        }
        .empty-state {
            text-align: center; padding: 60px 20px; color: #666;
        }
        .empty-state h3 { margin-bottom: 8px; color: #333; }
        @media (max-width: 768px) {
            .draft-header { flex-direction: column; align-items: flex-start; }
            .actions { width: 100%; } .btn { flex: 1; }
        }
    </style>
    <script>
        function handleAction(draftId, action) {
            fetch(`/api/drafts/${draftId}/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status) {
                    location.reload(); // Refresh to show updated state
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Network error');
            });
        }
        
        function editDraft(draftId) {
            const newText = prompt('Edit the draft reply:');
            if (newText) {
                fetch(`/api/drafts/${draftId}/edit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ draft_body: newText })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'updated') {
                        location.reload();
                    } else {
                        alert('Error: ' + (data.error || 'Unknown error'));
                    }
                });
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(() => location.reload(), 30000);
    </script>
</head>
<body>
    <div class="live-indicator">LIVE</div>
    <div class="container">
        <div class="header">
            <h1>Ennie Support Dashboard</h1>
            <p>Team Access • Real Support Emails • {{ pending_count }} Pending</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ pending_count }}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ approved_count }}</div>
                <div class="stat-label">Approved</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ escalated_count }}</div>
                <div class="stat-label">Escalated</div>
            </div>
        </div>
        
        {% if not drafts %}
        <div class="empty-state">
            <h3>All caught up! 🎉</h3>
            <p>No pending support emails right now.</p>
        </div>
        {% endif %}
        
        {% for draft in drafts %}
        <div class="draft-card {% if draft.escalate %}escalated{% endif %}">
            <div class="draft-header">
                <div class="contact">
                    <h3>{{ draft.from_name }}</h3>
                    <div class="email">{{ draft.from_email }}</div>
                    <div class="time">{{ draft.created_at }}</div>
                </div>
                <div class="tags">
                    {% if draft.classification %}
                    <span class="tag {{ draft.classification }}">{{ draft.classification.replace('_', ' ') }}</span>
                    {% endif %}
                    {% if draft.escalate %}
                    <span class="tag escalated">ESCALATED</span>
                    {% endif %}
                </div>
            </div>
            
            <div class="subject">{{ draft.subject }}</div>
            
            {% if draft.escalate and draft.escalation_reason %}
            <div class="escalation-reason">
                <h4>⚠️ Escalation Reason:</h4>
                {{ draft.escalation_reason }}
            </div>
            {% endif %}
            
            <div class="original">
                <h4>Original Email</h4>
                <p>{{ draft.body_original }}</p>
            </div>
            
            <div class="reply">
                <h4>AI Draft Reply</h4>
                <p>{{ draft.draft_body }}</p>
            </div>
            
            <div class="actions">
                <button class="btn btn-approve" onclick="handleAction('{{ draft.id }}', 'approve')">Approve</button>
                <button class="btn btn-edit" onclick="editDraft('{{ draft.id }}')">Edit</button>
                <button class="btn btn-reject" onclick="handleAction('{{ draft.id }}', 'reject')">Reject</button>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
'''

# Print all registered routes for debugging
print("[STARTUP] Registered routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.methods} {rule.rule}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)