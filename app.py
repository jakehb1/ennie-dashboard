#!/usr/bin/env python3
"""
Demo Dashboard with Real Support Emails
"""

from flask import Flask, render_template_string, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import json
import os
import hashlib
from datetime import datetime
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ennie-support-' + hashlib.sha256(b'ennie2026').hexdigest()[:16])

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', '') or os.environ.get('DATABASE_PUBLIC_URL', '') or 'postgresql://postgres:yHwzkRYETfjYvUqFSEnPICfnuclpcRGP@acela.proxy.rlwy.net:24999/railway'

def get_db():
    """Get a database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def init_db():
    """Create drafts table if it doesn't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            thread_id TEXT DEFAULT '',
            message_id TEXT DEFAULT '',
            from_email TEXT DEFAULT '',
            from_name TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            body_original TEXT DEFAULT '',
            draft_body TEXT DEFAULT '',
            original_draft_body TEXT DEFAULT '',
            classification TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            escalate BOOLEAN DEFAULT FALSE,
            escalation_reason TEXT DEFAULT '',
            escalation_notes TEXT DEFAULT '',
            escalated_to TEXT DEFAULT '',
            escalated_at TEXT DEFAULT '',
            escalation_response TEXT DEFAULT '',
            rejection_notes TEXT DEFAULT '',
            committee_model TEXT DEFAULT '',
            committee_confidence TEXT DEFAULT '',
            was_edited BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT '',
            approved_at TEXT DEFAULT '',
            edited_at TEXT DEFAULT '',
            rejected_at TEXT DEFAULT '',
            resolved_at TEXT DEFAULT '',
            re_escalated_at TEXT DEFAULT '',
            sent_at TEXT DEFAULT '',
            data JSONB DEFAULT '{}'
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_drafts_thread_id ON drafts(thread_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_drafts_message_id ON drafts(message_id)')
    # New columns for dashboard updates
    for col_def in [
        "approved_by TEXT DEFAULT ''",
        "claimed_by TEXT DEFAULT ''",
        "claimed_at TEXT DEFAULT ''",
        "urgency TEXT DEFAULT 'not_urgent'",
        "urgency_label TEXT DEFAULT ''",
        "hidden_trace_id TEXT DEFAULT ''",
        "rating INTEGER DEFAULT 0",
        "rated_by TEXT DEFAULT ''",
    ]:
        col_name = col_def.split()[0]
        try:
            cur.execute(f'ALTER TABLE drafts ADD COLUMN {col_def}')
        except Exception:
            pass  # Column already exists
    cur.close()
    conn.close()

def init_time_entries():
    """Create time_entries table for timesheet tracking."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            clock_in TEXT NOT NULL,
            clock_out TEXT DEFAULT '',
            duration_minutes REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_username ON time_entries(username)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_time_entries_clock_in ON time_entries(clock_in)')
    cur.close()
    conn.close()

# Initialize on startup
if DATABASE_URL:
    try:
        init_db()
        init_time_entries()
        print('✅ Postgres connected and drafts + time_entries tables ready')
    except Exception as e:
        print(f'⚠️ Postgres init failed: {e}')

# ── Admin users (username → PIN) ──────────────────────────────────────────────
ADMIN_USERS = {
    'jakeh':   os.environ.get('PIN_JAKEH',   '1234'),
    'casey':   os.environ.get('PIN_CASEY',   '1234'),
    'charlie': os.environ.get('PIN_CHARLIE', '1234'),
    'kara':    os.environ.get('PIN_KARA',    '1234'),
}

ADMIN_DISPLAY = {
    'jakeh':   'Jakeh',
    'casey':   'Casey',
    'charlie': 'Charlie',
    'kara':    'Kara',
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            # Return JSON 401 for API calls, redirect for pages
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def load_drafts():
    """Load all drafts from Postgres."""
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM drafts ORDER BY created_at DESC')
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f'load_drafts error: {e}')
        return []

def save_draft(draft):
    """Insert or update a single draft in Postgres."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO drafts (id, thread_id, message_id, from_email, from_name, subject,
                body_original, draft_body, original_draft_body, classification, status,
                escalate, escalation_reason, escalation_notes, escalated_to, escalated_at,
                escalation_response, rejection_notes, committee_model, committee_confidence,
                was_edited, created_at, approved_at, edited_at, rejected_at, resolved_at,
                re_escalated_at, sent_at,
                approved_by, claimed_by, claimed_at, urgency, urgency_label, hidden_trace_id,
                rating, rated_by)
            VALUES (%(id)s, %(thread_id)s, %(message_id)s, %(from_email)s, %(from_name)s,
                %(subject)s, %(body_original)s, %(draft_body)s, %(original_draft_body)s,
                %(classification)s, %(status)s, %(escalate)s, %(escalation_reason)s,
                %(escalation_notes)s, %(escalated_to)s, %(escalated_at)s,
                %(escalation_response)s, %(rejection_notes)s, %(committee_model)s,
                %(committee_confidence)s, %(was_edited)s, %(created_at)s, %(approved_at)s,
                %(edited_at)s, %(rejected_at)s, %(resolved_at)s, %(re_escalated_at)s, %(sent_at)s,
                %(approved_by)s, %(claimed_by)s, %(claimed_at)s, %(urgency)s, %(urgency_label)s, %(hidden_trace_id)s,
                %(rating)s, %(rated_by)s)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                draft_body = EXCLUDED.draft_body,
                original_draft_body = EXCLUDED.original_draft_body,
                escalation_notes = EXCLUDED.escalation_notes,
                escalated_to = EXCLUDED.escalated_to,
                escalated_at = EXCLUDED.escalated_at,
                escalation_response = EXCLUDED.escalation_response,
                rejection_notes = EXCLUDED.rejection_notes,
                was_edited = EXCLUDED.was_edited,
                approved_at = EXCLUDED.approved_at,
                edited_at = EXCLUDED.edited_at,
                rejected_at = EXCLUDED.rejected_at,
                resolved_at = EXCLUDED.resolved_at,
                re_escalated_at = EXCLUDED.re_escalated_at,
                sent_at = EXCLUDED.sent_at,
                approved_by = EXCLUDED.approved_by,
                claimed_by = EXCLUDED.claimed_by,
                claimed_at = EXCLUDED.claimed_at,
                urgency = EXCLUDED.urgency,
                urgency_label = EXCLUDED.urgency_label,
                hidden_trace_id = EXCLUDED.hidden_trace_id,
                rating = EXCLUDED.rating,
                rated_by = EXCLUDED.rated_by
        ''', {
            'id': draft.get('id', ''),
            'thread_id': draft.get('thread_id', ''),
            'message_id': draft.get('message_id', ''),
            'from_email': draft.get('from_email', ''),
            'from_name': draft.get('from_name', ''),
            'subject': draft.get('subject', ''),
            'body_original': draft.get('body_original', ''),
            'draft_body': draft.get('draft_body', ''),
            'original_draft_body': draft.get('original_draft_body', ''),
            'classification': draft.get('classification', ''),
            'status': draft.get('status', 'pending'),
            'escalate': bool(draft.get('escalate', False)),
            'escalation_reason': draft.get('escalation_reason', ''),
            'escalation_notes': draft.get('escalation_notes', ''),
            'escalated_to': draft.get('escalated_to', ''),
            'escalated_at': draft.get('escalated_at', ''),
            'escalation_response': draft.get('escalation_response', ''),
            'rejection_notes': draft.get('rejection_notes', ''),
            'committee_model': draft.get('committee_model', ''),
            'committee_confidence': draft.get('committee_confidence', ''),
            'was_edited': bool(draft.get('was_edited', False)),
            'created_at': draft.get('created_at', ''),
            'approved_at': draft.get('approved_at', ''),
            'edited_at': draft.get('edited_at', ''),
            'rejected_at': draft.get('rejected_at', ''),
            'resolved_at': draft.get('resolved_at', ''),
            're_escalated_at': draft.get('re_escalated_at', ''),
            'sent_at': draft.get('sent_at', ''),
            'approved_by': draft.get('approved_by', ''),
            'claimed_by': draft.get('claimed_by', ''),
            'claimed_at': draft.get('claimed_at', ''),
            'urgency': draft.get('urgency', 'not_urgent'),
            'urgency_label': draft.get('urgency_label', ''),
            'hidden_trace_id': draft.get('hidden_trace_id', ''),
            'rating': draft.get('rating', 0),
            'rated_by': draft.get('rated_by', ''),
        })
        cur.close()
        conn.close()
    except Exception as e:
        print(f'save_draft error: {e}')

def update_draft(draft_id, updates):
    """Update specific fields on a draft."""
    try:
        conn = get_db()
        cur = conn.cursor()
        set_parts = []
        vals = []
        for k, v in updates.items():
            set_parts.append(f'{k} = %s')
            vals.append(v)
        vals.append(draft_id)
        cur.execute(f"UPDATE drafts SET {', '.join(set_parts)} WHERE id = %s", vals)
        cur.close()
        conn.close()
        return cur.rowcount > 0
    except Exception as e:
        print(f'update_draft error: {e}')
        return False

def get_draft(draft_id):
    """Get a single draft by ID."""
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM drafts WHERE id = %s', (draft_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f'get_draft error: {e}')
        return None

def draft_exists(thread_id=None, message_id=None):
    """Check if a draft already exists by thread_id or message_id."""
    try:
        conn = get_db()
        cur = conn.cursor()
        if thread_id:
            cur.execute('SELECT 1 FROM drafts WHERE thread_id = %s LIMIT 1', (thread_id,))
            if cur.fetchone():
                cur.close(); conn.close()
                return True
        if message_id:
            cur.execute('SELECT 1 FROM drafts WHERE message_id = %s LIMIT 1', (message_id,))
            if cur.fetchone():
                cur.close(); conn.close()
                return True
        cur.close()
        conn.close()
        return False
    except Exception as e:
        print(f'draft_exists error: {e}')
        return False

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

# ── Support template (no-login view with full actions) ───────────────────────
SUPPORT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Ennie — Support Emails</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #000; background-image: radial-gradient(ellipse at 20% 50%, rgba(88,28,135,0.15) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(15,23,42,0.8) 0%, transparent 60%);
            min-height: 100vh; padding: 20px; color: rgba(255,255,255,0.9);
        }
        .container { max-width: 1000px; margin: 0 auto; }
        .header {
            background: rgba(255,255,255,0.04); backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
            border-radius: 16px; padding: 24px; margin-bottom: 24px; text-align: center;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .header h1 { color: #fff; font-size: 28px; margin: 0 0 8px 0; font-weight: 600; }
        .header p { color: rgba(255,255,255,0.5); margin: 0; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card {
            background: rgba(255,255,255,0.04); backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
            border-radius: 12px; padding: 16px; text-align: center;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .stat-number { font-size: 24px; font-weight: 700; color: #fff; margin-bottom: 4px; }
        .stat-label { color: rgba(255,255,255,0.45); font-size: 12px; text-transform: uppercase; font-weight: 500; letter-spacing: 0.5px; }
        .draft-card {
            background: rgba(255,255,255,0.05); backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
            border-radius: 16px; padding: 20px;
            margin-bottom: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .draft-card:hover { transform: translateY(-2px); box-shadow: 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08); }
        .draft-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
        .contact h3 { margin: 0 0 4px 0; color: #fff; font-size: 18px; font-weight: 600; }
        .contact .email { color: rgba(255,255,255,0.45); font-size: 14px; }
        .contact .time { color: rgba(255,255,255,0.3); font-size: 12px; margin-top: 2px; }
        .tag {
            background: rgba(0,122,255,0.2); color: #5AC8FA; padding: 4px 10px; border-radius: 12px;
            font-size: 11px; font-weight: 600; text-transform: capitalize;
        }
        .subject { font-weight: 600; margin-bottom: 10px; color: rgba(255,255,255,0.85); font-size: 15px; }
        .original, .reply { padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 14px; line-height: 1.5; }
        .original { background: rgba(0,122,255,0.06); border-left: 4px solid rgba(0,122,255,0.5); }
        .reply { background: rgba(52,199,89,0.06); border-left: 4px solid rgba(52,199,89,0.5); }
        .original h4, .reply h4 {
            margin: 0 0 6px 0; font-size: 11px; color: rgba(255,255,255,0.4);
            text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;
        }
        .original p { color: rgba(255,255,255,0.7); }
        .reply p { white-space: pre-line; line-height: 1.4; color: rgba(52,199,89,0.9); }
        .actions { display: flex; gap: 6px; flex-wrap: wrap; }
        .btn {
            padding: 8px 16px; border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            font-weight: 500; color: rgba(255,255,255,0.85); cursor: pointer; font-size: 13px;
            font-family: 'Inter', -apple-system, sans-serif; letter-spacing: -0.1px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            background: rgba(255,255,255,0.06); backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
        }
        .btn:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.18); transform: translateY(-0.5px); }
        .btn:active { transform: scale(0.97); }
        .btn-approve { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.9); border-color: rgba(255,255,255,0.15); }
        .btn-approve:hover { background: rgba(255,255,255,0.14); border-color: rgba(255,255,255,0.25); }
        .btn-edit { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.6); border-color: rgba(255,255,255,0.1); }
        .btn-edit:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.18); }
        .btn-escalate { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.6); border-color: rgba(255,255,255,0.1); }
        .btn-escalate:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.18); }
        .btn-reject { background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.4); border-color: rgba(255,255,255,0.08); }
        .btn-reject:hover { background: rgba(255,69,58,0.08); color: rgba(255,100,100,0.8); border-color: rgba(255,69,58,0.15); }
        .inline-edit-form {
            display: none; margin-top: 12px; padding: 14px;
            background: rgba(10,132,255,0.04);
            border-radius: 12px; border: 1px solid rgba(10,132,255,0.15);
        }
        .inline-edit-form.active { display: block; }
        .edit-textarea {
            width: 100%; min-height: 120px; padding: 12px; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px; font-family: inherit; font-size: 14px; line-height: 1.5;
            resize: vertical; background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.9);
        }
        .edit-textarea:focus { outline: none; border-color: rgba(10,132,255,0.4); box-shadow: 0 0 0 3px rgba(10,132,255,0.08); }
        .edit-actions { display: flex; gap: 8px; margin-top: 10px; justify-content: flex-end; }
        .btn-small {
            padding: 7px 14px; border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            font-weight: 500; color: rgba(255,255,255,0.85); cursor: pointer; font-size: 12px;
            font-family: 'Inter', -apple-system, sans-serif;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            background: rgba(255,255,255,0.06);
        }
        .btn-small:hover { background: rgba(255,255,255,0.1); }
        .btn-save { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.9); border-color: rgba(255,255,255,0.15); }
        .btn-cancel { background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.4); }
        .escalation-form {
            display: none; margin-top: 12px; padding: 14px; background: rgba(255,255,255,0.03);
            border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);
        }
        .escalation-form.active { display: block; }
        .escalation-textarea {
            width: 100%; height: 80px; padding: 8px; border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px; font-family: inherit; font-size: 13px;
            background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.9);
        }
        .escalation-textarea:focus { outline: none; border-color: rgba(255,149,0,0.5); }
        .escalation-note { font-size: 12px; color: rgba(255,149,0,0.8); margin-bottom: 8px; }
        @media (max-width: 768px) {
            .draft-header { flex-direction: column; align-items: flex-start; }
            .actions { width: 100%; } .btn { flex: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <nav style="display:flex;justify-content:space-between;align-items:center;padding:12px 0 20px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:24px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <img src="/static/ennie-logo.jpg" alt="Ennie" style="height:28px;width:auto;">
            </div>
            <a href="/login" style="font-size:13px;color:rgba(255,255,255,0.4);text-decoration:none;padding:6px 14px;border:1px solid rgba(255,255,255,0.1);border-radius:8px;transition:all 0.2s;">Admin Login</a>
        </nav>

        <div class="header">
            <h1>Support Emails</h1>
            <p>{{ total_count }} total emails</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_count }}</div>
                <div class="stat-label">Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ pending_count }}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ escalated_count }}</div>
                <div class="stat-label">Escalated</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ approved_count }}</div>
                <div class="stat-label">Handled</div>
            </div>
        </div>

        <div style="display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;">
            <a href="/support?status=all" style="padding:8px 16px;border-radius:10px;font-size:13px;font-weight:600;text-decoration:none;transition:all 0.2s;{% if status_filter == 'all' %}background:rgba(0,122,255,0.8);color:#fff;{% else %}background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.5);{% endif %}">All ({{ total_count }})</a>
            <a href="/support?status=pending" style="padding:8px 16px;border-radius:10px;font-size:13px;font-weight:600;text-decoration:none;transition:all 0.2s;{% if status_filter == 'pending' %}background:rgba(255,149,0,0.8);color:#fff;{% else %}background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.5);{% endif %}">Pending ({{ pending_count }})</a>
            <a href="/support?status=escalated" style="padding:8px 16px;border-radius:10px;font-size:13px;font-weight:600;text-decoration:none;transition:all 0.2s;{% if status_filter == 'escalated' %}background:rgba(255,59,48,0.8);color:#fff;{% else %}background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.5);{% endif %}">Escalated ({{ escalated_count }})</a>
            <a href="/support?status=approved" style="padding:8px 16px;border-radius:10px;font-size:13px;font-weight:600;text-decoration:none;transition:all 0.2s;{% if status_filter == 'approved' %}background:rgba(52,199,89,0.8);color:#fff;{% else %}background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.5);{% endif %}">Handled ({{ approved_count }})</a>
        </div>

        {% for draft in drafts %}
        <div class="draft-card" data-draft-id="{{ draft.id }}">
            <div class="draft-header">
                <div class="contact">
                    <h3>{{ draft.from_name }}</h3>
                    <div class="email">{{ draft.from_email }}</div>
                    <div class="time">{{ draft.created_at }}</div>
                </div>
                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                    {% set st = draft.status or 'pending' %}
                    <span style="font-size:11px;font-weight:700;text-transform:uppercase;padding:3px 8px;border-radius:6px;
                        {% if st == 'pending' %}background:rgba(255,255,255,0.06);color:rgba(255,200,100,0.7);border:1px solid rgba(255,200,100,0.1);
                        {% elif st == 'escalated' %}background:rgba(255,255,255,0.06);color:rgba(255,100,100,0.8);border:1px solid rgba(255,100,100,0.12);
                        {% elif st == 'approved' or st == 'sent' %}background:rgba(255,255,255,0.04);color:rgba(255,255,255,0.5);
                        {% elif st == 'rejected' %}background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.4);
                        {% elif st == 'resolved' %}background:rgba(0,122,255,0.15);color:#5AC8FA;
                        {% else %}background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.4);
                        {% endif %}">{{ st }}</span>
                    <div class="tag">{{ (draft.classification or 'general').replace('_', ' ') }}</div>
                </div>
            </div>

            <div class="subject">{{ draft.subject }}</div>

            <div class="original">
                <h4>Original Email</h4>
                <p>{{ draft.body_original }}</p>
            </div>

            <div class="reply">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                    <h4 style="margin:0;">AI Draft Reply</h4>
                    {% if draft.committee_confidence %}
                    {% set conf_raw = draft.committee_confidence|string|replace('%','')|float(0) %}
                    {% if conf_raw <= 5 %}{% set conf_pct = (conf_raw / 5 * 100)|round|int %}{% else %}{% set conf_pct = conf_raw|round|int %}{% endif %}
                    <span style="font-size:11px;font-weight:600;padding:4px 10px;border-radius:20px;white-space:nowrap;
                        {% if conf_pct >= 80 %}background:rgba(52,199,89,0.12);color:#34C759;border:1px solid rgba(52,199,89,0.15);
                        {% elif conf_pct >= 50 %}background:rgba(255,159,10,0.12);color:#FF9F0A;border:1px solid rgba(255,159,10,0.15);
                        {% else %}background:rgba(255,69,58,0.12);color:#FF453A;border:1px solid rgba(255,69,58,0.15);{% endif %}">
                        {% if conf_pct >= 80 %}✦{% elif conf_pct >= 50 %}◉{% else %}⚠{% endif %} AI Confidence: {{ conf_pct }}%
                    </span>
                    {% endif %}
                </div>
                <p class="draft-preview">{{ draft.draft_body }}</p>

                <div class="inline-edit-form" id="edit-form-{{ draft.id }}">
                    <textarea class="edit-textarea" id="edit-text-{{ draft.id }}">{{ draft.draft_body }}</textarea>
                    <div class="edit-actions">
                        <button class="btn-small btn-save" onclick="saveEdit('{{ draft.id }}')">Save & Approve</button>
                        <button class="btn-small btn-cancel" onclick="cancelEdit('{{ draft.id }}')">Cancel</button>
                    </div>
                </div>

                <div class="escalation-form" id="escalation-form-{{ draft.id }}">
                    <div class="escalation-note">Escalating — select who to send to:</div>
                    <select id="escalation-to-{{ draft.id }}" style="width:100%;padding:8px 10px;border:1px solid rgba(255,255,255,0.1);border-radius:6px;font-size:13px;margin-bottom:8px;background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.9);">
                        <option value="casey" selected>Casey</option>
                        <option value="jakeh">Jakeh</option>
                        <option value="charlie">Charlie</option>
                        <option value="kara">Kara</option>
                    </select>
                    <textarea class="escalation-textarea" id="escalation-text-{{ draft.id }}" placeholder="Add context (optional)"></textarea>
                    <div class="edit-actions">
                        <button class="btn-small" style="background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.9);border-color:rgba(255,255,255,0.15);" onclick="saveEscalation('{{ draft.id }}')">Escalate</button>
                        <button class="btn-small btn-cancel" onclick="cancelEscalation('{{ draft.id }}')">Cancel</button>
                    </div>
                </div>
            </div>

            {% if draft.approved_by and draft.status in ('approved', 'sent') %}
            <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:8px;">Approved by <strong style="color:rgba(255,255,255,0.7);">{{ draft.approved_by }}</strong> at {{ draft.approved_at }}</div>
            {% endif %}

            {% if (draft.status or 'pending') == 'pending' %}
            <div class="actions">
                <button class="btn btn-approve" onclick="approveDraft('{{ draft.id }}')">Approve</button>
                <button class="btn btn-edit" onclick="showEditForm('{{ draft.id }}')">Edit</button>
                <button class="btn btn-escalate" onclick="showEscalationForm('{{ draft.id }}')">Escalate</button>
                <button class="btn btn-reject" onclick="rejectDraft('{{ draft.id }}')">Reject</button>
            </div>
            {% endif %}
        </div>
        {% endfor %}

        {% if not drafts %}
        <div style="text-align:center;padding:60px 20px;">
            <div style="font-size:48px;margin-bottom:16px;">✓</div>
            <h3 style="font-size:20px;font-weight:600;color:#fff;margin-bottom:8px;">All clear!</h3>
            <p style="font-size:15px;color:rgba(255,255,255,0.45);">No emails matching this filter.</p>
        </div>
        {% endif %}
    </div>

    <script>
    function toast(message, type) {
      const el = document.createElement('div');
      el.textContent = message;
      el.style.cssText = `position:fixed;top:20px;right:20px;z-index:1000;background:rgba(255,255,255,0.1);backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);color:white;padding:12px 16px;border-radius:10px;font-size:14px;font-weight:500;box-shadow:0 8px 32px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.1);transition:all 0.3s ease;opacity:0;transform:translateY(-20px);`;
      if (type === 'success') { el.style.background = 'rgba(52,199,89,0.85)'; el.style.borderColor = 'rgba(52,199,89,0.3)'; }
      if (type === 'error') { el.style.background = 'rgba(255,59,48,0.85)'; el.style.borderColor = 'rgba(255,59,48,0.3)'; }
      document.body.appendChild(el);
      requestAnimationFrame(() => { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; });
      setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(-20px)'; setTimeout(() => el.remove(), 300); }, 3000);
    }

    async function apiPost(url, data) {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data || {}) });
      return r.json();
    }

    function removeDraftCard(id) {
      const card = document.querySelector('[data-draft-id="' + id + '"]');
      if (!card) return;
      card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      card.style.opacity = '0'; card.style.transform = 'translateX(20px)';
      setTimeout(() => { card.remove(); if (!document.querySelectorAll('.draft-card').length) location.reload(); }, 300);
    }

    function approveDraft(id) {
      apiPost('/api/support/' + id + '/approve').then(res => {
        if (res.ok) { removeDraftCard(id); toast('Draft approved!', 'success'); }
        else toast('Error: ' + (res.error || 'Something went wrong'), 'error');
      }).catch(() => toast('Network error', 'error'));
    }

    function rejectDraft(id) {
      const reason = prompt('Rejection reason (optional):') || '';
      apiPost('/api/support/' + id + '/reject', { notes: reason }).then(res => {
        if (res.ok) { removeDraftCard(id); toast('Draft rejected'); }
        else toast('Error: ' + (res.error || 'Something went wrong'), 'error');
      });
    }

    function showEditForm(id) {
      document.querySelectorAll('.inline-edit-form.active, .escalation-form.active').forEach(f => f.classList.remove('active'));
      const form = document.getElementById('edit-form-' + id);
      if (form) { form.classList.add('active'); document.getElementById('edit-text-' + id)?.focus(); }
    }
    function cancelEdit(id) { document.getElementById('edit-form-' + id)?.classList.remove('active'); }

    function saveEdit(id) {
      const text = document.getElementById('edit-text-' + id)?.value.trim();
      if (!text) { toast('Draft text cannot be empty', 'error'); return; }
      apiPost('/api/support/' + id + '/edit', { draft_text: text }).then(res => {
        if (res.ok) { removeDraftCard(id); toast('Draft edited and approved!', 'success'); }
        else toast('Error: ' + (res.error || 'Something went wrong'), 'error');
      });
    }

    function showEscalationForm(id) {
      document.querySelectorAll('.inline-edit-form.active, .escalation-form.active').forEach(f => f.classList.remove('active'));
      const form = document.getElementById('escalation-form-' + id);
      if (form) { form.classList.add('active'); document.getElementById('escalation-text-' + id)?.focus(); }
    }
    function cancelEscalation(id) { document.getElementById('escalation-form-' + id)?.classList.remove('active'); }

    function saveEscalation(id) {
      const to = document.getElementById('escalation-to-' + id)?.value || 'jakeh';
      const notes = document.getElementById('escalation-text-' + id)?.value.trim() || '';
      const names = { jakeh: 'Jakeh', casey: 'Casey', charlie: 'Charlie', kara: 'Kara' };
      apiPost('/api/support/' + id + '/escalate', { to, notes }).then(res => {
        if (res.ok) { removeDraftCard(id); toast('Escalated to ' + (names[to] || to), 'success'); }
        else toast('Error: ' + (res.error || 'Something went wrong'), 'error');
      });
    }
    </script>
</body>
</html>
'''

# ── Auth routes ──────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip().lower()
        pin = (request.form.get('pin') or '').strip()
        if username in ADMIN_USERS and ADMIN_USERS[username] == pin:
            session['user'] = username
            session['display_name'] = ADMIN_DISPLAY.get(username, username)
            session['trace_id'] = uuid.uuid4().hex[:12]  # Hidden watermark per session
            # Auto clock-in on login
            try:
                conn = get_db()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT id FROM time_entries WHERE username = %s AND clock_out = '' LIMIT 1", (username,))
                if not cur.fetchone():
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cur.execute("INSERT INTO time_entries (username, clock_in, created_at) VALUES (%s, %s, %s)", (username, now, now))
                cur.close()
                conn.close()
            except Exception as e:
                print(f'Auto clock-in error: {e}')
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Wrong PIN. Try again.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Auto clock-out on logout
    user = session.get('user', '')
    if user:
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM time_entries WHERE username = %s AND clock_out = '' ORDER BY clock_in DESC LIMIT 1", (user,))
            row = cur.fetchone()
            if row:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                try:
                    clock_in_dt = datetime.strptime(row['clock_in'], '%Y-%m-%d %H:%M:%S')
                    duration = (datetime.now() - clock_in_dt).total_seconds() / 60.0
                except Exception:
                    duration = 0
                cur.execute("UPDATE time_entries SET clock_out = %s, duration_minutes = %s WHERE id = %s", (now, round(duration, 1), row['id']))
            cur.close()
            conn.close()
        except Exception as e:
            print(f'Auto clock-out error: {e}')
    session.clear()
    return redirect(url_for('login'))

@app.route('/health')
@app.route('/healthz')
def health_check():
    """Unauthenticated health check endpoint — keeps Railway from sleeping the service."""
    try:
        # Quick DB connectivity check
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        return jsonify({'status': 'healthy', 'db': 'connected', 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'db': 'error', 'error': str(e)}), 503


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Webhook endpoint for support runner."""
    if request.method == 'GET':
        return jsonify({'status': 'webhook ready', 'methods': ['GET', 'POST']})
    
    # Handle POST request
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
            'committee_model': data.get('committee_model', ''),
            'committee_confidence': str(data.get('committee_confidence', '')),
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hidden_trace_id': uuid.uuid4().hex[:12],
        }
        
        save_draft(new_draft)
        
        return jsonify({'id': draft_id, 'status': 'created'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts', methods=['GET', 'POST'])
def handle_drafts():
    """Handle both GET and POST for drafts."""
    if request.method == 'POST':
        try:
            data = request.get_json() or {}
            draft_id = str(uuid.uuid4())
            
            new_draft = {
                'id': draft_id,
                'thread_id': data.get('thread_id', ''),
                'message_id': data.get('message_id', ''),
                'from_email': data.get('from_email') or data.get('sender_email', ''),
                'from_name': data.get('from_name') or data.get('sender_name', ''),
                'subject': data.get('subject', ''),
                'body_original': data.get('body_original') or data.get('original_content', ''),
                'draft_body': data.get('draft_body') or data.get('draft_response', ''),
                'classification': data.get('classification') or data.get('email_analysis', {}).get('category', ''),
                'escalate': bool(data.get('escalate', False)),
                'escalation_reason': data.get('escalation_reason', ''),
                'committee_model': data.get('committee_model', ''),
                'committee_confidence': data.get('committee_confidence', ''),
                'status': 'pending',
                'created_at': data.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            save_draft(new_draft)
            
            return jsonify({'id': draft_id, 'status': 'created'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET request - return drafts
    drafts = load_drafts()
    pending = [d for d in drafts if d.get('status') == 'pending']
    return jsonify(pending)

@app.route('/api/test', methods=['GET', 'POST'])
def api_test():
    """Test endpoint to verify API is working."""
    if request.method == 'POST':
        return jsonify({'method': 'POST', 'status': 'success'})
    # Debug: check DB status
    db_status = 'no DATABASE_URL'
    db_count = 0
    db_error = None
    if DATABASE_URL:
        db_status = 'configured'
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM drafts')
            db_count = cur.fetchone()[0]
            cur.close()
            conn.close()
            db_status = 'connected'
        except Exception as e:
            db_error = str(e)[:200]
            db_status = 'error'
    # Show all env vars that start with DB or PG or RAILWAY or DATABASE
    env_keys = [k for k in os.environ if any(p in k.upper() for p in ['DB', 'PG', 'DATABASE', 'POSTGRES'])]
    env_hints = {k: os.environ[k][:20] + '...' for k in env_keys}
    return jsonify({'method': 'GET', 'status': 'success', 'db_status': db_status, 'db_count': db_count, 'db_error': db_error, 'db_url_set': bool(DATABASE_URL), 'env_hints': env_hints})

@app.route('/support')
def support_view():
    """Public support view — no login required, full actions (approve/edit/escalate)."""
    all_drafts = load_drafts()
    
    status_filter = request.args.get('status', 'all')
    if status_filter == 'all':
        drafts = all_drafts
    else:
        drafts = [d for d in all_drafts if d.get('status') == status_filter]
    
    status_order = {'pending': 0, 'escalated': 1, 'approved': 2, 'sent': 3, 'rejected': 4, 'resolved': 5}
    drafts.sort(key=lambda d: (status_order.get(d.get('status', ''), 99), d.get('created_at', '')), reverse=False)
    
    pending_count = len([d for d in all_drafts if d.get('status') == 'pending'])
    escalated_count = len([d for d in all_drafts if d.get('status') == 'escalated'])
    approved_count = len([d for d in all_drafts if d.get('status') in ('approved', 'sent')])
    total_count = len(all_drafts)
    
    return render_template_string(SUPPORT_TEMPLATE,
        drafts=drafts, total_count=total_count, pending_count=pending_count,
        escalated_count=escalated_count, approved_count=approved_count,
        status_filter=status_filter)

@app.route('/')
@login_required
def dashboard():
    return redirect(url_for('inbox_page'))

@app.route('/api/drafts/<draft_id>/approve', methods=['POST'])
@login_required
def approve_draft(draft_id):
    """Approve a draft as-is."""
    try:
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        approver = session.get('user', 'unknown')
        updates = {
            'was_edited': False,
            'status': 'approved',
            'approved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'approved_by': approver,
        }
        if not draft.get('original_draft_body'):
            updates['original_draft_body'] = draft.get('draft_body', '')
        update_draft(draft_id, updates)
        return jsonify({'ok': True, 'status': 'approved', 'approved_by': approver})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/reject', methods=['POST'])
@login_required
def reject_draft(draft_id):
    try:
        data = request.get_json() or {}
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {
            'status': 'rejected',
            'rejected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'rejection_notes': data.get('notes', ''),
        })
        return jsonify({'ok': True, 'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/escalate', methods=['POST'])
@login_required
def escalate_draft(draft_id):
    try:
        data = request.get_json() or {}
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {
            'status': 'escalated',
            'escalated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'escalation_notes': data.get('notes', ''),
            'escalated_to': data.get('to', 'jakeh'),
        })
        return jsonify({'ok': True, 'status': 'escalated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/edit', methods=['POST'])
@login_required
def edit_draft(draft_id):
    try:
        data = request.get_json() or {}
        draft_text = data.get('draft_text', '').strip()
        if not draft_text:
            return jsonify({'error': 'Draft text required'}), 400
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        approver = session.get('user', 'unknown')
        updates = {
            'draft_body': draft_text,
            'was_edited': True,
            'status': 'approved',
            'edited_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'approved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'approved_by': approver,
        }
        if not draft.get('original_draft_body'):
            updates['original_draft_body'] = draft.get('draft_body', '')
        update_draft(draft_id, updates)
        return jsonify({'ok': True, 'status': 'edited_and_approved', 'approved_by': approver})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/claim', methods=['POST'])
@login_required
def claim_draft(draft_id):
    """Claim a draft for the current user — locks it from others."""
    try:
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        if draft.get('claimed_by') and draft['claimed_by'] != session.get('user', ''):
            return jsonify({'error': f'Already claimed by {ADMIN_DISPLAY.get(draft["claimed_by"], draft["claimed_by"])}'}), 409
        user = session.get('user', 'unknown')
        update_draft(draft_id, {
            'claimed_by': user,
            'claimed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        return jsonify({'ok': True, 'claimed_by': user})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/unclaim', methods=['POST'])
@login_required
def unclaim_draft(draft_id):
    """Release a claimed draft."""
    try:
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        if draft.get('claimed_by') and draft['claimed_by'] != session.get('user', ''):
            return jsonify({'error': 'Not your claim'}), 403
        update_draft(draft_id, {'claimed_by': '', 'claimed_at': ''})
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/urgency', methods=['POST'])
@login_required
def set_urgency(draft_id):
    """Set urgency label on a draft."""
    try:
        data = request.get_json() or {}
        urgency = data.get('urgency', 'not_urgent')
        if urgency not in ('not_urgent', 'moderate', 'urgent'):
            return jsonify({'error': 'Invalid urgency. Use: not_urgent, moderate, urgent'}), 400
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {'urgency': urgency, 'urgency_label': session.get('user', 'unknown')})
        return jsonify({'ok': True, 'urgency': urgency})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/rate', methods=['POST'])
@login_required
def rate_draft(draft_id):
    """Rate a draft response 1-5 stars for training."""
    try:
        data = request.get_json() or {}
        rating = data.get('rating', 0)
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be 1-5'}), 400
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {'rating': rating, 'rated_by': session.get('user', 'unknown')})
        return jsonify({'ok': True, 'rating': rating})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Local regen server running on Mac Studio, exposed via Cloudflare tunnel
# URL is registered dynamically by the tunnel startup script
_regen_server_url = os.environ.get('REGEN_SERVER_URL', 'https://restaurant-hired-euros-wave.trycloudflare.com')
REGEN_SECRET = os.environ.get('REGEN_SECRET', 'ennie-regen-2026')

@app.route('/api/regen-url', methods=['POST'])
def register_regen_url():
    """Called by the local tunnel script to register its current URL."""
    global _regen_server_url
    data = request.get_json() or {}
    if data.get('secret') != REGEN_SECRET:
        return jsonify({'error': 'Invalid secret'}), 403
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL required'}), 400
    _regen_server_url = url
    return jsonify({'ok': True, 'url': url})

@app.route('/api/drafts/<draft_id>/regenerate', methods=['POST'])
@login_required
def regenerate_draft(draft_id):
    """Regenerate AI draft by calling back to local regen server."""
    try:
        import requests as req
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        
        # Mark as regenerating
        update_draft(draft_id, {'status': 'regenerating'})
        
        # Call local regen server
        r = req.post(
            f'{_regen_server_url}/regenerate',
            json={
                'body_original': draft.get('body_original', ''),
                'subject': draft.get('subject', ''),
                'from_name': draft.get('from_name', ''),
                'from_email': draft.get('from_email', ''),
            },
            headers={'X-Regen-Secret': REGEN_SECRET},
            timeout=90,
        )
        r.raise_for_status()
        result = r.json()
        
        new_draft_body = result.get('draft_body', '')
        if not new_draft_body:
            raise ValueError('Empty response from regen server')
        
        # Save the original if not already saved, then update with new draft
        updates = {
            'draft_body': new_draft_body,
            'status': 'pending',
            'was_edited': False,
        }
        if not draft.get('original_draft_body'):
            updates['original_draft_body'] = draft.get('draft_body', '')
        
        update_draft(draft_id, updates)
        return jsonify({'ok': True, 'message': 'Draft regenerated', 'draft_body': new_draft_body})
    except Exception as e:
        # Revert status on failure
        update_draft(draft_id, {'status': 'pending'})
        return jsonify({'error': f'Regeneration failed: {str(e)}'}), 500


@app.route('/api/escalations/stale', methods=['GET'])
@login_required
def stale_escalations():
    """Return escalations older than 24 hours that haven't been resolved."""
    try:
        drafts = load_drafts()
        stale = []
        now = datetime.now()
        for d in drafts:
            if d.get('status') != 'escalated':
                continue
            esc_at = d.get('escalated_at', '')
            if not esc_at:
                continue
            try:
                esc_time = datetime.strptime(esc_at, '%Y-%m-%d %H:%M:%S')
                hours = (now - esc_time).total_seconds() / 3600
                if hours >= 24:
                    d['hours_stale'] = round(hours, 1)
                    stale.append(d)
            except ValueError:
                continue
        return jsonify({'stale': stale, 'count': len(stale)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
@login_required
def search_emails():
    """Search all emails by sender, subject, or body content."""
    try:
        q = request.args.get('q', '').strip().lower()
        if not q or len(q) < 2:
            return jsonify({'results': [], 'query': q, 'count': 0})
        
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT * FROM drafts
            WHERE LOWER(from_email) LIKE %(q)s
               OR LOWER(from_name) LIKE %(q)s
               OR LOWER(subject) LIKE %(q)s
               OR LOWER(body_original) LIKE %(q)s
               OR LOWER(draft_body) LIKE %(q)s
            ORDER BY created_at DESC
            LIMIT 50
        ''', {'q': f'%{q}%'})
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        
        # Serialize
        for r in rows:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
                elif isinstance(v, bool):
                    r[k] = v
        
        return jsonify({'results': rows, 'query': q, 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/approved-drafts', methods=['GET'])
def get_approved_drafts():
    drafts = load_drafts()
    approved = [d for d in drafts if d.get('status') == 'approved']
    return jsonify(approved)

@app.route('/api/drafts/<draft_id>/mark-sent', methods=['POST'])
def mark_draft_sent(draft_id):
    try:
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {
            'status': 'sent',
            'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        return jsonify({'ok': True, 'status': 'sent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sent-examples', methods=['GET'])
def get_sent_examples():
    """Return sent drafts for learning."""
    """Query params: limit (default 20), edited_only (default false)"""
    limit = request.args.get('limit', 20, type=int)
    edited_only = request.args.get('edited_only', 'false').lower() == 'true'
    
    drafts = load_drafts()
    sent = [d for d in drafts if d.get('status') == 'sent']
    
    if edited_only:
        sent = [d for d in sent if d.get('was_edited', False)]
    
    # Return most recent first, limited
    examples = []
    for d in sent[:limit]:
        examples.append({
            'id': d.get('id'),
            'subject': d.get('subject', ''),
            'from_email': d.get('from_email', ''),
            'body_original': d.get('body_original', ''),
            'classification': d.get('classification', ''),
            'original_draft_body': d.get('original_draft_body', d.get('draft_body', '')),
            'final_response': d.get('draft_body', ''),
            'was_edited': d.get('was_edited', False),
            'sent_at': d.get('sent_at', ''),
        })
    
    return jsonify(examples)

@app.route('/lookup')
@login_required
def lookup_page():
    """Render the lookup page."""
    return render_template('lookup.html')

@app.route('/api/lookup', methods=['GET'])
@login_required
def lookup_user():
    """Look up user across Kajabi, Eventbrite, and Klaviyo."""
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email parameter required'}), 400
    
    try:
        import requests
        import csv
        import os
        
        # API credentials
        EB_TOKEN = "NVPWHF7QOKK74KQ6ZF3W"
        EB_ORG_ID = "393488177349"
        KLAVIYO_API_KEY = "pk_b426e39ad5065a9eed02cde3b28d0a46a0"
        
        results = {
            'email': email,
            'kajabi': {'found': False, 'summary': 'Not found', 'name': None, 'products': [], 'status': None},
            'eventbrite': {'found': False, 'orders': [], 'summary': 'No orders found'},
            'klaviyo': {'found': False, 'summary': 'Not found'}
        }
        
        # Kajabi CSV lookup - contact info
        kajabi_contact = None
        try:
            kajabi_csv_path = "/Users/robotclaw/.openclaw/media/inbound/kajabi_contacts_latest.csv"
            
            with open(kajabi_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('email', '').strip().lower() == email:
                        kajabi_contact = row
                        break
        except Exception:
            pass
        
        # Kajabi Product Progress lookup  
        kajabi_products = []
        try:
            progress_csv_path = "/Users/robotclaw/.openclaw/media/inbound/ProductProgressReport_Site_2147522759_Product_2149292408_1bc---15124abe-056f-4731-a8fe-bc0103d0df35.csv"
            
            with open(progress_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Email', '').strip().lower() == email:
                        progress = row.get('Product Progress', '0')
                        logins = row.get('Logins', '0') 
                        start_date = row.get('Start Date', '')
                        last_activity = row.get('Last Activity At', '')
                        
                        kajabi_products.append({
                            'name': 'Energy Healing Course',  # This specific CSV is for one course
                            'progress': f"{progress}%" if progress and progress != '0' else '0%',
                            'logins': logins,
                            'start_date': start_date,
                            'last_activity': last_activity
                        })
                        break
        except Exception:
            pass
        
        # Combine Kajabi data
        if kajabi_contact or kajabi_products:
            name = kajabi_contact.get('name', '').strip() if kajabi_contact else 'Unknown'
            subscribed = kajabi_contact.get('subscribed', '').strip() == 'True' if kajabi_contact else False
            created = kajabi_contact.get('created_at', '')[:10] if kajabi_contact and kajabi_contact.get('created_at') else ''
            
            summary_parts = []
            if kajabi_contact:
                summary_parts.append(f"{name} ({'subscribed' if subscribed else 'unsubscribed'})")
                if created:
                    summary_parts.append(f"member since {created}")
            
            if kajabi_products:
                for product in kajabi_products:
                    summary_parts.append(f"{product['name']}: {product['progress']} progress, {product['logins']} logins")
            
            results['kajabi'] = {
                'found': True,
                'name': name,
                'subscribed': subscribed if kajabi_contact else None,
                'created': created,
                'products': kajabi_products,
                'summary': " • ".join(summary_parts) if summary_parts else "Found in Kajabi"
            }
        else:
            results['kajabi']['summary'] = f"Not found in Kajabi records"
        
        # Eventbrite lookup
        try:
            headers = {"Authorization": f"Bearer {EB_TOKEN}"}
            r = requests.get(
                f"https://www.eventbriteapi.com/v3/organizations/{EB_ORG_ID}/orders/",
                headers=headers,
                params={"only_emails": email, "expand": "event,attendees"},
                timeout=10
            )
            
            if r.ok:
                orders = []
                for order in r.json().get("orders", []):
                    if order.get("email", "").lower() == email:
                        event = order.get("event", {})
                        attendees = order.get("attendees", [])
                        ticket_class = attendees[0].get("ticket_class_name", "General") if attendees else "General"
                        
                        orders.append({
                            'event_name': event.get("name", {}).get("text", "Unknown Event"),
                            'event_date': event.get("start", {}).get("local", "")[:10],
                            'ticket_type': ticket_class,
                            'status': order.get("status", "unknown")
                        })
                
                if orders:
                    results['eventbrite'] = {
                        'found': True,
                        'orders': orders,
                        'summary': f"Found {len(orders)} event registration(s)"
                    }
        except Exception as e:
            results['eventbrite']['summary'] = f"Eventbrite error: {str(e)[:50]}"
        
        # Klaviyo lookup
        try:
            headers = {
                "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
                "revision": "2024-02-15"
            }
            r = requests.get("https://a.klaviyo.com/api/profiles/",
                headers=headers,
                params={"filter": f'equals(email,"{email}")'},
                timeout=8)
                
            if r.ok and r.json().get("data"):
                profile = r.json()["data"][0]
                attrs = profile["attributes"]
                name = f"{attrs.get('first_name','')} {attrs.get('last_name','')}".strip()
                created = attrs.get("created", "")[:10]
                
                results['klaviyo'] = {
                    'found': True,
                    'summary': f"Found in Klaviyo: {name} (subscribed {created})"
                }
        except Exception as e:
            results['klaviyo']['summary'] = f"Klaviyo error: {str(e)[:50]}"
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Lookup failed: {str(e)}'}), 500

# ── Template-based page routes ──────────────────────────────────────────────

@app.route('/inbox')
@login_required
def inbox_page():
    """Render the inbox page — the main working view."""
    from flask import render_template
    all_drafts = load_drafts()

    # Stats
    total_count = len(all_drafts)
    pending_count = len([d for d in all_drafts if d.get('status') == 'pending'])
    escalated_count = len([d for d in all_drafts if d.get('status') == 'escalated'])
    handled_count = len([d for d in all_drafts if d.get('status') in ('approved', 'sent')])

    # Pending drafts sorted: urgent first, then oldest first
    pending = [d for d in all_drafts if d.get('status') == 'pending']
    # Sort: newest first (urgent emails still prioritized at top)
    pending.sort(key=lambda d: d.get('created_at', ''), reverse=True)
    # Then stable-sort urgent to top
    urgency_order = {'urgent': 0, 'moderate': 1, 'not_urgent': 2, '': 2}
    pending.sort(key=lambda d: urgency_order.get(d.get('urgency', ''), 2))

    return render_template('inbox.html',
        drafts=pending,
        total_count=total_count,
        pending_count=pending_count,
        escalated_count=escalated_count,
        handled_count=handled_count
    )

@app.route('/escalations')
@login_required
def escalations_page():
    """Render the escalations page. Default: show user's own. ?view=all for everything."""
    drafts = load_drafts()
    escalated = [d for d in drafts if d.get('status') == 'escalated']
    
    view = request.args.get('view', 'mine')
    current_user = session.get('user', '')
    
    if view == 'all':
        filtered = escalated
    else:
        filtered = [e for e in escalated if e.get('escalated_to', '').lower() == current_user]
    
    return render_template('escalations.html',
                           escalations=filtered,
                           all_escalations_count=len(escalated),
                           my_escalations_count=len([e for e in escalated if e.get('escalated_to', '').lower() == current_user]),
                           current_view=view,
                           display_name=session.get('display_name', 'Admin'))

@app.route('/api/escalations/<esc_id>/respond', methods=['POST'])
@login_required
def respond_escalation(esc_id):
    try:
        data = request.get_json() or {}
        response = data.get('response', '').strip()
        if not response:
            return jsonify({'error': 'Response text required'}), 400
        if not get_draft(esc_id):
            return jsonify({'error': 'Escalation not found'}), 404
        update_draft(esc_id, {
            'status': 'resolved',
            'escalation_response': response,
            'resolved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        return jsonify({'ok': True, 'status': 'resolved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/escalations/<esc_id>/re-escalate', methods=['POST'])
@login_required
def re_escalate(esc_id):
    try:
        data = request.get_json() or {}
        if not get_draft(esc_id):
            return jsonify({'error': 'Escalation not found'}), 404
        update_draft(esc_id, {
            'escalated_to': data.get('to', 'jakeh'),
            'escalation_notes': data.get('notes', ''),
            're_escalated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        return jsonify({'ok': True, 'status': 're-escalated', 'to': data.get('to', 'jakeh')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Public support API (no login required) ───────────────────────────────────

@app.route('/api/support/<draft_id>/approve', methods=['POST'])
def support_approve(draft_id):
    try:
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        approver = session.get('user', 'support_agent')
        updates = {'was_edited': False, 'status': 'approved', 'approved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'approved_by': approver}
        if not draft.get('original_draft_body'):
            updates['original_draft_body'] = draft.get('draft_body', '')
        update_draft(draft_id, updates)
        return jsonify({'ok': True, 'status': 'approved', 'approved_by': approver})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/support/<draft_id>/reject', methods=['POST'])
def support_reject(draft_id):
    try:
        data = request.get_json() or {}
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {
            'status': 'rejected',
            'rejected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'rejection_notes': data.get('notes', ''),
        })
        return jsonify({'ok': True, 'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/support/<draft_id>/escalate', methods=['POST'])
def support_escalate(draft_id):
    try:
        data = request.get_json() or {}
        if not get_draft(draft_id):
            return jsonify({'error': 'Draft not found'}), 404
        update_draft(draft_id, {
            'status': 'escalated',
            'escalated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'escalation_notes': data.get('notes', ''),
            'escalated_to': data.get('to', 'jakeh'),
        })
        return jsonify({'ok': True, 'status': 'escalated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/support/<draft_id>/edit', methods=['POST'])
def support_edit(draft_id):
    try:
        data = request.get_json() or {}
        draft_text = data.get('draft_text', '').strip()
        if not draft_text:
            return jsonify({'error': 'Draft text required'}), 400
        draft = get_draft(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        approver = session.get('user', 'support_agent')
        updates = {
            'draft_body': draft_text, 'was_edited': True, 'status': 'approved',
            'edited_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'approved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'approved_by': approver,
        }
        if not draft.get('original_draft_body'):
            updates['original_draft_body'] = draft.get('draft_body', '')
        update_draft(draft_id, updates)
        return jsonify({'ok': True, 'status': 'edited_and_approved', 'approved_by': approver})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Bulk import endpoint (for backfill) ──────────────────────────────────────

@app.route('/api/bulk-import', methods=['POST'])
def bulk_import():
    """Import multiple email records at once. Expects {emails: [...]}.
    Protected by a simple token in header: X-Import-Token.
    """
    token = request.headers.get('X-Import-Token', '')
    expected = os.environ.get('IMPORT_TOKEN', 'ennie-backfill-2026')
    if token != expected:
        return jsonify({'error': 'Invalid import token'}), 403
    
    try:
        data = request.get_json() or {}
        emails = data.get('emails', [])
        if not emails:
            return jsonify({'error': 'No emails to import'}), 400
        
        imported = 0
        skipped = 0
        for email in emails:
            tid = email.get('thread_id', '')
            mid = email.get('message_id', '')
            if draft_exists(thread_id=tid, message_id=mid):
                skipped += 1
                continue
            
            draft_id = str(uuid.uuid4())
            new_draft = {
                'id': draft_id,
                'thread_id': tid,
                'message_id': mid,
                'from_email': email.get('from_email') or email.get('sender_email', ''),
                'from_name': email.get('from_name') or email.get('sender_name', ''),
                'subject': email.get('subject', ''),
                'body_original': email.get('body_original') or email.get('original_content', ''),
                'draft_body': email.get('draft_body') or email.get('draft_response', ''),
                'classification': email.get('classification', ''),
                'status': email.get('status', 'sent'),
                'created_at': email.get('created_at') or email.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            save_draft(new_draft)
            imported += 1
        
        return jsonify({'ok': True, 'imported': imported, 'skipped': skipped})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Timesheet routes ─────────────────────────────────────────────────────────

@app.route('/timesheet')
@login_required
def timesheet_page():
    """Render the timesheet page."""
    return render_template('timesheet.html')

@app.route('/api/timesheet/status', methods=['GET'])
@login_required
def timesheet_status():
    """Check if current user is clocked in."""
    try:
        user = session.get('user', '')
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM time_entries
            WHERE username = %s AND clock_out = ''
            ORDER BY clock_in DESC LIMIT 1
        """, (user,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return jsonify({'clocked_in': True, 'entry': dict(row)})
        return jsonify({'clocked_in': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timesheet/clock-in', methods=['POST'])
@login_required
def timesheet_clock_in():
    """Clock in the current user."""
    try:
        user = session.get('user', '')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Check not already clocked in
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id FROM time_entries
            WHERE username = %s AND clock_out = ''
            LIMIT 1
        """, (user,))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({'error': 'Already clocked in'}), 409
        cur.execute("""
            INSERT INTO time_entries (username, clock_in, created_at)
            VALUES (%s, %s, %s) RETURNING id
        """, (user, now, now))
        entry_id = cur.fetchone()['id']
        cur.close()
        conn.close()
        return jsonify({'ok': True, 'id': entry_id, 'clock_in': now})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timesheet/clock-out', methods=['POST'])
@login_required
def timesheet_clock_out():
    """Clock out the current user."""
    try:
        user = session.get('user', '')
        data = request.get_json() or {}
        notes = data.get('notes', '').strip()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM time_entries
            WHERE username = %s AND clock_out = ''
            ORDER BY clock_in DESC LIMIT 1
        """, (user,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify({'error': 'Not clocked in'}), 409
        # Calculate duration
        try:
            clock_in_dt = datetime.strptime(row['clock_in'], '%Y-%m-%d %H:%M:%S')
            clock_out_dt = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
            duration = (clock_out_dt - clock_in_dt).total_seconds() / 60.0
        except Exception:
            duration = 0
        cur.execute("""
            UPDATE time_entries SET clock_out = %s, duration_minutes = %s, notes = %s
            WHERE id = %s
        """, (now, round(duration, 1), notes, row['id']))
        cur.close()
        conn.close()
        return jsonify({'ok': True, 'duration_minutes': round(duration, 1), 'clock_out': now})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timesheet/entries', methods=['GET'])
@login_required
def timesheet_entries():
    """Get time entries. Optional filters: user, days (default 7)."""
    try:
        target_user = request.args.get('user', '')
        days = request.args.get('days', 7, type=int)
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cutoff = (datetime.now() - __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        if target_user:
            cur.execute("""
                SELECT * FROM time_entries
                WHERE username = %s AND clock_in >= %s
                ORDER BY clock_in DESC
            """, (target_user, cutoff))
        else:
            cur.execute("""
                SELECT * FROM time_entries
                WHERE clock_in >= %s
                ORDER BY clock_in DESC
            """, (cutoff,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'entries': rows, 'count': len(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timesheet/summary', methods=['GET'])
@login_required
def timesheet_summary():
    """Get summary stats per user for the given period. Optional: days (default 7)."""
    try:
        days = request.args.get('days', 7, type=int)
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cutoff = (datetime.now() - __import__('datetime').timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("""
            SELECT username,
                   COUNT(*) as sessions,
                   COALESCE(SUM(duration_minutes), 0) as total_minutes
            FROM time_entries
            WHERE clock_in >= %s AND clock_out != ''
            GROUP BY username
            ORDER BY total_minutes DESC
        """, (cutoff,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        # Format
        for r in rows:
            mins = r['total_minutes']
            r['total_hours'] = round(mins / 60, 1)
            r['display_name'] = ADMIN_DISPLAY.get(r['username'], r['username'])
        return jsonify({'summary': rows, 'days': days})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timesheet/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_time_entry(entry_id):
    """Delete a time entry (own entries only)."""
    try:
        user = session.get('user', '')
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM time_entries WHERE id = %s', (entry_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify({'error': 'Entry not found'}), 404
        if row['username'] != user:
            cur.close(); conn.close()
            return jsonify({'error': 'Can only delete your own entries'}), 403
        cur.execute('DELETE FROM time_entries WHERE id = %s', (entry_id,))
        cur.close()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timesheet/manual', methods=['POST'])
@login_required
def timesheet_manual_entry():
    """Manually add a completed time entry."""
    try:
        user = session.get('user', '')
        data = request.get_json() or {}
        clock_in = data.get('clock_in', '').strip()
        clock_out = data.get('clock_out', '').strip()
        notes = data.get('notes', '').strip()
        if not clock_in or not clock_out:
            return jsonify({'error': 'clock_in and clock_out required'}), 400
        try:
            ci = datetime.strptime(clock_in, '%Y-%m-%d %H:%M')
            co = datetime.strptime(clock_out, '%Y-%m-%d %H:%M')
            duration = (co - ci).total_seconds() / 60.0
            if duration <= 0:
                return jsonify({'error': 'clock_out must be after clock_in'}), 400
        except ValueError:
            return jsonify({'error': 'Format: YYYY-MM-DD HH:MM'}), 400
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("""
            INSERT INTO time_entries (username, clock_in, clock_out, duration_minutes, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (user, ci.strftime('%Y-%m-%d %H:%M:%S'), co.strftime('%Y-%m-%d %H:%M:%S'), round(duration, 1), notes, now))
        entry_id = cur.fetchone()['id']
        cur.close()
        conn.close()
        return jsonify({'ok': True, 'id': entry_id, 'duration_minutes': round(duration, 1)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)