#!/usr/bin/env python3
"""
Simple Ennie Dashboard for Railway - Real Data Only
"""

from flask import Flask, render_template_string
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "ennie-simple"

DATABASE = "/tmp/support.db"

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY,
            thread_id TEXT,
            from_email TEXT,
            from_name TEXT,
            subject TEXT,
            body_original TEXT,
            draft_body TEXT,
            classification TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # Add the 5 real support emails directly
    real_emails = [
        ('real-linda', 'alushlifetravel@yahoo.com', 'Linda Edwards', 
         'Re: Energy Teaching: Q&A Session #2 ✨',
         'Hello,Was there a teaching marathon this week? I don\'t have it scheduled and only have the 3:00 healing session for Saturday at this time on my calendar.',
         'Hi Linda,\n\nThank you for your question about this week\'s schedule. The regular teaching marathon wasn\'t scheduled this week, so you\'re seeing the correct calendar with just the 3:00 PM healing session on Saturday.\n\nFor future scheduling updates, we recommend checking our main calendar or email announcements.\n\nBest regards,\nCharlie Goldsmith Support Team',
         'event_question'),
        
        ('real-bev', 'bevbyers33@gmail.com', 'Bev Byers',
         'Re: Group Healing with Charlie ❤️',
         'I attended group healing 2 weeks ago for the first time and booked in successfully using my iPhone. I\'m trying to book again for this session on 25th April but every time I try there\'s an issue.',
         'Hi Bev,\n\nThank you for reaching out about your booking issue. This sounds like a technical problem with the booking system. Let me help you get registered for the April 25th session.\n\nI\'ll send you a direct booking link that should work properly. Please try that and let me know if you continue having issues.\n\nBest regards,\nCharlie Goldsmith Support Team',
         'event_booking_issue'),
         
        ('real-cari', 'carifrederick22@gmail.com', 'Cari Hoffbeck',
         'Re: Charlie\'s First Teaching in Two Years 😊',
         'Hi! My mother was ill and passed away right before the 3 day event in March so I did not purchase. If I purchase it now, will there be a recording available?',
         'Hi Cari,\n\nFirst, I\'m so sorry for your loss. That must have been an incredibly difficult time.\n\nYes, recordings are available for the 3-day teaching event. Even though you missed the live sessions, you can still access all the content at your own pace.\n\nI\'ll send you the purchase link and details about accessing the recordings.\n\nWith compassion,\nCharlie Goldsmith Support Team',
         'can_i_still_sign_up'),
         
        ('real-laurel', 'laurelfishman@gmail.com', 'Laurel Fishman',
         'Followup: Saturday Group Healing with Charlie',
         'Hello again, I appreciate your attention to this! Please clarify how this will work. Will you be emailing the numeric meeting ID and the numeric passcode right before the meeting starts?',
         'Hi Laurel,\n\nGreat question! Yes, we\'ll send you the Zoom meeting details (ID and passcode) via email about 30 minutes before the Saturday healing session begins.\n\nThe session starts at 3:00 PM your local time. Please check your email around 2:30 PM for the access information.\n\nSee you on Saturday!\nCharlie Goldsmith Support Team',
         'event_question'),
         
        ('real-susan', 'fotofino@aol.com', 'Susan Fino',
         'April25 healing',
         'Hi, yesterday I paid for the April 25th healing session and I did not get receipt or confirmation. Checked spam and junk no messages. I tried getting into Eventbrite to check tickets and wouldn\'t let me.',
         'Hi Susan,\n\nI can help you with your confirmation issue. Let me look up your registration for the April 25th healing session.\n\nEventbrite sometimes has delays with confirmation emails. I\'ll resend your ticket confirmation right now to fotofino@aol.com.\n\nYou should receive it within the next few minutes. If you don\'t see it, please check your spam folder one more time.\n\nBest regards,\nCharlie Goldsmith Support Team',
         'missing_eventbrite_confirmation')
    ]
    
    for thread_id, email, name, subject, body, draft, classification in real_emails:
        db.execute("""
            INSERT OR REPLACE INTO drafts 
            (thread_id, from_email, from_name, subject, body_original, draft_body, classification)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (thread_id, email, name, subject, body, draft, classification))
    
    db.commit()
    db.close()

@app.route('/')
def dashboard():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    drafts = db.execute("SELECT * FROM drafts WHERE status='pending' ORDER BY from_name").fetchall()
    db.close()
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Ennie Support Dashboard - Real Data</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; padding: 20px; min-height: 100vh; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { background: rgba(255,255,255,0.1); backdrop-filter: blur(20px); border-radius: 16px; padding: 24px; margin-bottom: 24px; text-align: center; border: 1px solid rgba(255,255,255,0.2); }
        .header h1 { color: white; font-size: 28px; margin: 0 0 8px 0; }
        .header p { color: rgba(255,255,255,0.8); margin: 0; }
        .draft-card { background: rgba(255,255,255,0.95); border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
        .draft-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
        .contact h3 { margin: 0 0 4px 0; color: #1a1a1a; }
        .contact .email { color: #666; font-size: 14px; }
        .tag { background: #007AFF; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .tag.event_question { background: #34C759; }
        .tag.event_booking_issue { background: #FF9500; }
        .tag.can_i_still_sign_up { background: #AF52DE; }
        .tag.missing_eventbrite_confirmation { background: #FF3B30; }
        .subject { font-weight: 600; margin-bottom: 12px; color: #333; }
        .original, .reply { padding: 16px; border-radius: 8px; margin-bottom: 16px; }
        .original { background: #f8f9fa; border-left: 4px solid #007AFF; }
        .reply { background: #e8f5e8; border-left: 4px solid #34C759; }
        .original h4, .reply h4 { margin: 0 0 8px 0; font-size: 12px; color: #666; text-transform: uppercase; }
        .reply p { white-space: pre-line; line-height: 1.5; }
        .actions { display: flex; gap: 12px; flex-wrap: wrap; }
        .btn { padding: 10px 16px; border-radius: 8px; border: none; font-weight: 600; color: white; cursor: pointer; }
        .btn-approve { background: #34C759; }
        .btn-edit { background: #007AFF; }
        .btn-escalate { background: #FF9500; }
        .btn-reject { background: #FF3B30; }
        @media (max-width: 768px) { .draft-header { flex-direction: column; align-items: flex-start; } .actions { width: 100%; } .btn { flex: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Ennie Support Dashboard</h1>
            <p>Real Support Emails • {{ drafts|length }} Pending</p>
        </div>
        
        {% for draft in drafts %}
        <div class="draft-card">
            <div class="draft-header">
                <div class="contact">
                    <h3>{{ draft.from_name }}</h3>
                    <div class="email">{{ draft.from_email }}</div>
                </div>
                <div class="tag {{ draft.classification }}">{{ draft.classification.replace('_', ' ').title() }}</div>
            </div>
            
            <div class="subject">{{ draft.subject }}</div>
            
            <div class="original">
                <h4>Original Email</h4>
                <p>{{ draft.body_original }}</p>
            </div>
            
            <div class="reply">
                <h4>Draft Reply</h4>
                <p>{{ draft.draft_body }}</p>
            </div>
            
            <div class="actions">
                <button class="btn btn-approve">✓ Approve</button>
                <button class="btn btn-edit">✎ Edit + Approve</button>
                <button class="btn btn-escalate">⚠ Escalate</button>
                <button class="btn btn-reject">✗ Reject</button>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
    ''', drafts=drafts)

@app.route('/reset')
def reset():
    init_db()
    return 'Database reset with real emails. <a href="/">View Dashboard</a>'

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))