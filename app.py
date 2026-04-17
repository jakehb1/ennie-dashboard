#!/usr/bin/env python3
"""
Demo Dashboard with Real Support Emails
"""

from flask import Flask, render_template_string, request, jsonify
import json
import os
import sqlite3
from datetime import datetime
import uuid

app = Flask(__name__)

# Simple file-based storage for drafts (Railway-friendly)
DRAFTS_FILE = os.path.join('/tmp', 'ennie_drafts.json')

def load_drafts():
    """Load drafts from JSON file."""
    try:
        with open(DRAFTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_drafts(drafts):
    """Save drafts to JSON file."""
    with open(DRAFTS_FILE, 'w') as f:
        json.dump(drafts, f, indent=2)

# Real support emails data
real_emails = [
    {
        "id": 1,
        "thread_id": "real-linda-edwards",
        "from_email": "alushlifetravel@yahoo.com",
        "from_name": "Linda Edwards",
        "subject": "Re: Energy Teaching: Q&A Session #2 ✨",
        "body_original": "Hello,Was there a teaching marathon this week? I don't have it scheduled and only have the 3:00 healing session for Saturday at this time on my calendar. Is it possible to get a schedule for at least the next few weeks?",
        "draft_body": "Hi Linda,\n\nThank you for your question about this week's schedule. The regular teaching marathon wasn't scheduled this week, so you're seeing the correct calendar with just the 3:00 PM healing session on Saturday.\n\nFor future scheduling updates, we recommend checking our main calendar or email announcements. I'll also send you a link to the updated schedule.\n\nBest regards,\nCharlie Goldsmith Support Team",
        "classification": "event_question",
        "status": "pending",
        "created_at": "2026-04-16 10:30"
    },
    {
        "id": 2,
        "thread_id": "real-bev-byers",
        "from_email": "bevbyers33@gmail.com",
        "from_name": "Bev Byers",
        "subject": "Re: Group Healing with Charlie ❤️",
        "body_original": "I attended group healing 2 weeks ago for the first time and booked in successfully using my iPhone. I'm trying to book again for this session on 25th April but every time I try there's an issue with the booking system.",
        "draft_body": "Hi Bev,\n\nI can help you with your booking issue. This sounds like a technical problem with the booking system. Let me send you a direct booking link that should work properly.\n\nPlease try this link and let me know if you continue having issues. I'll also check the mobile booking system.\n\nBest regards,\nCharlie Goldsmith Support Team",
        "classification": "event_booking_issue",
        "status": "pending",
        "created_at": "2026-04-16 11:15"
    },
    {
        "id": 3,
        "thread_id": "real-abigail-bloom",
        "from_email": "abigailbloom14@gmail.com",
        "from_name": "Abigail Bloom",
        "subject": "Re: Energy Teaching: 3 day intensive recordings",
        "body_original": "Hi, I attended the 3 day intensive but missed a couple sessions due to work commitments. Are the recordings available for purchase? I'd really like to catch up on what I missed.",
        "draft_body": "Hi Abigail,\n\nThank you for attending our 3-day intensive! Yes, recordings are available for participants who missed sessions.\n\nI'll send you access information for the missed sessions within the next hour. Please check your email for the recording links.\n\nBest regards,\nCharlie Goldsmith Support Team",
        "classification": "recording_access",
        "status": "pending",
        "created_at": "2026-04-16 12:45"
    },
    {
        "id": 4,
        "thread_id": "real-carmen-gill",
        "from_email": "cgill0508@gmail.com",
        "from_name": "Carmen Gill",
        "subject": "Re: Energy Teaching: Q&A Session This Weekend ❤️",
        "body_original": "Hi there! I signed up for the Q&A session this weekend but haven't received the Zoom link yet. Could you please send it to me? Also, what time zone is the session in?",
        "draft_body": "Hi Carmen,\n\nThank you for signing up for this weekend's Q&A session! The session is at 2:00 PM Pacific Time.\n\nI'll resend your Zoom access information right now. Please check your email within the next few minutes for the meeting details.\n\nSee you this weekend!\nCharlie Goldsmith Support Team",
        "classification": "event_question",
        "status": "pending",
        "created_at": "2026-04-16 14:20"
    }
]

@app.route('/submit', methods=['POST'])
def submit_draft():
    """Simple endpoint for support runner to submit drafts."""
    try:
        data = request.get_json() or {}
        draft_id = str(uuid.uuid4())
        
        new_draft = {
            'id': draft_id,
            'thread_id': data.get('thread_id', ''),
            'message_id': data.get('message_id', ''),
            'from_email': data.get('from_email', ''),
            'from_name': data.get('from_name', ''),
            'subject': data.get('subject', ''),
            'body_original': data.get('body_original', ''),
            'draft_body': data.get('draft_body', ''),
            'classification': data.get('classification', ''),
            'escalate': bool(data.get('escalate', False)),
            'escalation_reason': data.get('escalation_reason', ''),
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        drafts = load_drafts()
        drafts.insert(0, new_draft)  # Add to front
        save_drafts(drafts)
        
        return f'{{"id":"{draft_id}","status":"created"}}', 201
    except Exception as e:
        return f'{{"error":"{str(e)}"}}', 500

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    """Get all pending drafts."""
    drafts = load_drafts()
    pending = [d for d in drafts if d.get('status') == 'pending']
    return jsonify(pending)

@app.route('/api/test', methods=['GET', 'POST'])
def api_test():
    """Test endpoint to verify API is working."""
    if request.method == 'POST':
        return jsonify({'method': 'POST', 'status': 'success'})
    return jsonify({'method': 'GET', 'status': 'success'})

@app.route('/')
def dashboard():
    # Load real drafts from file, fallback to demo data
    file_drafts = [d for d in load_drafts() if d.get('status') == 'pending']
    drafts = file_drafts if file_drafts else [d for d in real_emails if d['status'] == 'pending']
    
    # Calculate stats
    event_count = len([d for d in drafts if d.get('classification', '').find('event') >= 0])
    healing_count = len([d for d in drafts if d.get('classification', '').find('healing') >= 0])
    
    return render_template_string('''
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
        .subject { font-weight: 600; margin-bottom: 10px; color: #333; font-size: 15px; }
        .original, .reply { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; line-height: 1.5; }
        .original { background: #f8f9fa; border-left: 4px solid #007AFF; }
        .reply { background: #e8f5e8; border-left: 4px solid #34C759; }
        .original h4, .reply h4 {
            margin: 0 0 6px 0; font-size: 11px; color: #666;
            text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;
        }
        .reply p { white-space: pre-line; line-height: 1.4; color: #2d5a2d; }
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
        @media (max-width: 768px) {
            .draft-header { flex-direction: column; align-items: flex-start; }
            .actions { width: 100%; } .btn { flex: 1; }
        }
    </style>
</head>
<body>
    <div class="live-indicator">LIVE</div>
    <div class="container">
        <div class="header">
            <h1>Ennie Support Dashboard</h1>
            <p>Team Access • Real Support Emails • {{ drafts|length }} Pending</p>
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
        
        {% for draft in drafts %}
        <div class="draft-card">
            <div class="draft-header">
                <div class="contact">
                    <h3>{{ draft.from_name }}</h3>
                    <div class="email">{{ draft.from_email }}</div>
                    <div class="time">{{ draft.created_at }}</div>
                </div>
                <div class="tag {{ draft.classification }}">{{ draft.classification.replace('_', ' ') }}</div>
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
                <button class="btn btn-approve">Approve</button>
                <button class="btn btn-edit">Edit</button>
                <button class="btn btn-escalate">Escalate</button>
                <button class="btn btn-reject">Reject</button>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
    ''', drafts=drafts, event_count=event_count, healing_count=healing_count)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)