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
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        drafts = load_drafts()
        drafts.insert(0, new_draft)  # Add to front
        save_drafts(drafts)
        
        return jsonify({'id': draft_id, 'status': 'created'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts', methods=['GET', 'POST'])
def handle_drafts():
    """Handle both GET and POST for drafts."""
    if request.method == 'POST':
        # Create new draft
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
            drafts.insert(0, new_draft)
            save_drafts(drafts)
            
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
        .user-link { color: inherit; text-decoration: none; cursor: pointer; }
        .user-link:hover { text-decoration: underline; color: #007AFF; }
        .modal-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000;
            background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
            opacity: 0; visibility: hidden; transition: all 0.3s ease;
        }
        .modal-overlay.active { opacity: 1; visibility: visible; }
        .modal {
            background: white; border-radius: 16px; max-width: 800px; width: 90vw; max-height: 80vh;
            overflow-y: auto; box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            transform: translateY(20px) scale(0.95); transition: all 0.3s ease;
        }
        .modal-overlay.active .modal { transform: translateY(0) scale(1); }
        .modal-header {
            padding: 20px 24px; border-bottom: 1px solid #eee;
            display: flex; justify-content: between; align-items: center;
        }
        .modal-title { margin: 0; font-size: 20px; font-weight: 600; }
        .modal-close {
            background: none; border: none; font-size: 24px; cursor: pointer;
            color: #666; margin-left: auto;
        }
        .modal-body { padding: 24px; }
        .lookup-card {
            background: #f8f9fa; border-radius: 12px; padding: 16px; margin-bottom: 16px;
            border-left: 4px solid #007AFF;
        }
        .lookup-card h4 { margin: 0 0 12px 0; font-size: 16px; display: flex; align-items: center; gap: 8px; }
        .lookup-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .lookup-key { font-weight: 600; color: #666; }
        .lookup-val { color: #333; }
        .tag-list { display: flex; gap: 6px; flex-wrap: wrap; }
        .tag { 
            background: #007AFF; color: white; padding: 2px 8px; border-radius: 12px;
            font-size: 11px; font-weight: 500;
        }
        .not-found { color: #999; font-style: italic; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .inline-edit-form { 
            display: none; margin-top: 12px; padding: 12px; background: #f8f9fa; 
            border-radius: 8px; border: 2px solid #007AFF;
        }
        .inline-edit-form.active { display: block; }
        .edit-textarea {
            width: 100%; min-height: 120px; padding: 12px; border: 1px solid #ddd;
            border-radius: 6px; font-family: inherit; font-size: 14px; line-height: 1.5;
            resize: vertical;
        }
        .edit-actions {
            display: flex; gap: 8px; margin-top: 8px; justify-content: flex-end;
        }
        .btn-small {
            padding: 6px 12px; border-radius: 4px; border: none;
            font-weight: 500; color: white; cursor: pointer; font-size: 12px;
        }
        .btn-save { background: #34C759; }
        .btn-cancel { background: #666; }
        .escalation-form {
            display: none; margin-top: 12px; padding: 12px; background: #fff3cd;
            border-radius: 8px; border: 2px solid #FF9500;
        }
        .escalation-form.active { display: block; }
        .escalation-textarea {
            width: 100%; height: 80px; padding: 8px; border: 1px solid #ddd;
            border-radius: 4px; font-family: inherit; font-size: 13px;
        }
        .escalation-note { font-size: 12px; color: #856404; margin-bottom: 8px; }
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
        <div class="draft-card" data-draft-id="{{ draft.id }}">
            <div class="draft-header">
                <div class="contact">
                    <h3><a href="#" class="user-link" onclick="lookupUser('{{ draft.from_email }}', '{{ draft.from_name }}'); return false;">{{ draft.from_name }}</a></h3>
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
                <p class="draft-preview">{{ draft.draft_body }}</p>
                
                <!-- Inline Edit Form -->
                <div class="inline-edit-form" id="edit-form-{{ draft.id }}">
                    <textarea class="edit-textarea" id="edit-text-{{ draft.id }}" placeholder="Edit the draft response...">{{ draft.draft_body }}</textarea>
                    <div class="edit-actions">
                        <button class="btn-small btn-save" onclick="saveEdit('{{ draft.id }}')">Save & Approve</button>
                        <button class="btn-small btn-cancel" onclick="cancelEdit('{{ draft.id }}')">Cancel</button>
                    </div>
                </div>
                
                <!-- Inline Escalation Form -->
                <div class="escalation-form" id="escalation-form-{{ draft.id }}">
                    <div class="escalation-note">⚠️ Escalating to human review - add notes below:</div>
                    <textarea class="escalation-textarea" id="escalation-text-{{ draft.id }}" placeholder="Why does this need human attention? (optional)"></textarea>
                    <div class="edit-actions">
                        <button class="btn-small" style="background: #FF9500;" onclick="saveEscalation('{{ draft.id }}')">Escalate</button>
                        <button class="btn-small btn-cancel" onclick="cancelEscalation('{{ draft.id }}')">Cancel</button>
                    </div>
                </div>
            </div>
            
            <div class="actions">
                <button class="btn btn-approve" onclick="approveDraft('{{ draft.id }}')">Approve</button>
                <button class="btn btn-edit" onclick="showEditForm('{{ draft.id }}')">Edit</button>
                <button class="btn btn-escalate" onclick="showEscalationForm('{{ draft.id }}')">Escalate</button>
                <button class="btn btn-reject" onclick="rejectDraft('{{ draft.id }}')">Reject</button>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <!-- User Lookup Modal -->
    <div class="modal-overlay" id="lookup-modal">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title" id="lookup-title">User Lookup</h3>
                <button class="modal-close" onclick="closeLookupModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div id="lookup-loading" style="text-align: center; padding: 40px;">
                    <div style="display: inline-block; width: 32px; height: 32px; border: 3px solid #f3f3f3; border-radius: 50%; border-top: 3px solid #007AFF; animation: spin 1s linear infinite;"></div>
                    <p style="margin-top: 16px; color: #666;">Loading user data...</p>
                </div>
                <div id="lookup-results" style="display: none;"></div>
            </div>
        </div>
    </div>
    
    <script>
/* ── Draft actions ──────────────────────────────────────────────────────── */

// ── Toast notifications ──────────────────────────────────────────────────────
function toast(message, type) {
  const el = document.createElement('div');
  el.textContent = message;
  el.className = 'toast' + (type ? ' toast-' + type : '');
  el.style.cssText = `
    position: fixed; top: 20px; right: 20px; z-index: 1000;
    background: #333; color: white; padding: 12px 16px;
    border-radius: 8px; font-size: 14px; font-weight: 500;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    transition: all 0.3s ease; opacity: 0; transform: translateY(-20px);
  `;
  if (type === 'success') el.style.background = '#34C759';
  if (type === 'error') el.style.background = '#FF3B30';
  
  document.body.appendChild(el);
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
  });
  
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-20px)';
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

// ── API helpers ──────────────────────────────────────────────────────────────
async function apiPost(url, data) {
  const r = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data || {}),
  });
  return r.json();
}

// ── Draft card removal ───────────────────────────────────────────────────────
function removeDraftCard(id) {
  const card = document.querySelector('[data-draft-id="' + id + '"]');
  if (!card) return;
  card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  card.style.opacity = '0';
  card.style.transform = 'translateX(20px)';
  setTimeout(() => {
    card.remove();
    // Check if no drafts left
    const remaining = document.querySelectorAll('.draft-card').length;
    if (remaining === 0) {
      location.reload(); // Refresh to show updated stats
    }
  }, 300);
}

// ── Actions ───────────────────────────────────────────────────────────────────
function approveDraft(id) {
  apiPost('/api/drafts/' + id + '/approve').then(res => {
    if (res.ok) { 
      removeDraftCard(id); 
      toast('Draft approved and ready to send!', 'success'); 
    } else { 
      toast('Error: ' + (res.error || 'Something went wrong'), 'error'); 
    }
  }).catch(() => toast('Network error', 'error'));
}

function rejectDraft(id) {
  const reason = prompt('Rejection reason (optional):') || '';
  apiPost('/api/drafts/' + id + '/reject', { notes: reason }).then(res => {
    if (res.ok) { 
      removeDraftCard(id); 
      toast('Draft rejected'); 
    } else { 
      toast('Error: ' + (res.error || 'Something went wrong'), 'error'); 
    }
  });
}

function showEscalationForm(id) {
  // Hide any other open forms first
  document.querySelectorAll('.inline-edit-form.active, .escalation-form.active').forEach(form => {
    form.classList.remove('active');
  });
  
  const form = document.getElementById('escalation-form-' + id);
  if (form) {
    form.classList.add('active');
    const textarea = document.getElementById('escalation-text-' + id);
    if (textarea) textarea.focus();
  }
}

function cancelEscalation(id) {
  const form = document.getElementById('escalation-form-' + id);
  if (form) form.classList.remove('active');
}

function saveEscalation(id) {
  const textarea = document.getElementById('escalation-text-' + id);
  const notes = textarea ? textarea.value.trim() : '';
  
  apiPost('/api/drafts/' + id + '/escalate', { to: 'cassie', notes }).then(res => {
    if (res.ok) { 
      removeDraftCard(id); 
      toast('Escalated for human review', 'success'); 
    } else { 
      toast('Error: ' + (res.error || 'Something went wrong'), 'error'); 
    }
  });
}

function showEditForm(id) {
  // Hide any other open forms first
  document.querySelectorAll('.inline-edit-form.active, .escalation-form.active').forEach(form => {
    form.classList.remove('active');
  });
  
  const form = document.getElementById('edit-form-' + id);
  if (form) {
    form.classList.add('active');
    const textarea = document.getElementById('edit-text-' + id);
    if (textarea) {
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    }
  }
}

function cancelEdit(id) {
  const form = document.getElementById('edit-form-' + id);
  if (form) form.classList.remove('active');
}

function saveEdit(id) {
  const textarea = document.getElementById('edit-text-' + id);
  const newText = textarea ? textarea.value.trim() : '';
  
  if (!newText) {
    toast('Draft text cannot be empty', 'error');
    return;
  }
  
  apiPost('/api/drafts/' + id + '/edit', { draft_text: newText }).then(res => {
    if (res.ok) { 
      removeDraftCard(id); 
      toast('Draft edited and approved!', 'success'); 
    } else { 
      toast('Error: ' + (res.error || 'Something went wrong'), 'error'); 
    }
  });
}

// ── User Lookup ──────────────────────────────────────────────────────────────
function lookupUser(email, name) {
  document.getElementById('lookup-title').textContent = `${name} (${email})`;
  document.getElementById('lookup-loading').style.display = 'block';
  document.getElementById('lookup-results').style.display = 'none';
  document.getElementById('lookup-modal').classList.add('active');
  
  fetch(`/api/lookup?email=${encodeURIComponent(email)}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById('lookup-results').innerHTML = `<p class="not-found">Error: ${data.error}</p>`;
      } else {
        renderLookupData(data);
      }
      document.getElementById('lookup-loading').style.display = 'none';
      document.getElementById('lookup-results').style.display = 'block';
    })
    .catch(e => {
      document.getElementById('lookup-results').innerHTML = `<p class="not-found">Network error: ${e.message}</p>`;
      document.getElementById('lookup-loading').style.display = 'none';
      document.getElementById('lookup-results').style.display = 'block';
    });
}

function renderLookupData(data) {
  const { kajabi, eventbrite, klaviyo } = data;
  let html = '';
  
  // Kajabi section
  html += '<div class="lookup-card">';
  html += '<h4>🏛 Kajabi</h4>';
  if (kajabi.found) {
    if (kajabi.name) html += `<div class="lookup-row"><span class="lookup-key">Name</span><span class="lookup-val">${kajabi.name}</span></div>`;
    if (kajabi.logins) html += `<div class="lookup-row"><span class="lookup-key">Logins</span><span class="lookup-val">${kajabi.logins}</span></div>`;
    if (kajabi.last_active) html += `<div class="lookup-row"><span class="lookup-key">Last Active</span><span class="lookup-val">${kajabi.last_active}</span></div>`;
    if (kajabi.offers && kajabi.offers.length) {
      html += '<div class="lookup-row"><span class="lookup-key">Offers</span><div class="tag-list">';
      kajabi.offers.forEach(offer => html += `<span class="tag">${offer}</span>`);
      html += '</div></div>';
    }
    if (kajabi.tags && kajabi.tags.length) {
      html += '<div class="lookup-row"><span class="lookup-key">Tags</span><div class="tag-list">';
      kajabi.tags.forEach(tag => html += `<span class="tag">${tag}</span>`);
      html += '</div></div>';
    }
  } else {
    html += `<p class="not-found">${kajabi.summary}</p>`;
  }
  html += '</div>';
  
  // Eventbrite section
  html += '<div class="lookup-card">';
  html += '<h4>🎫 Eventbrite</h4>';
  if (eventbrite.found && eventbrite.orders.length) {
    eventbrite.orders.forEach(order => {
      html += '<div style="padding: 8px 0; border-bottom: 1px solid #eee; margin-bottom: 8px;">';
      html += `<div style="font-weight: 600; margin-bottom: 4px;">${order.event_name}</div>`;
      html += `<div style="font-size: 13px; color: #666;">${order.event_date} • ${order.ticket_type} • ${order.status}</div>`;
      html += '</div>';
    });
  } else {
    html += `<p class="not-found">${eventbrite.summary}</p>`;
  }
  html += '</div>';
  
  // Klaviyo section
  html += '<div class="lookup-card">';
  html += '<h4>📧 Klaviyo</h4>';
  if (klaviyo.found) {
    html += `<p>${klaviyo.summary}</p>`;
  } else {
    html += `<p class="not-found">${klaviyo.summary}</p>`;
  }
  html += '</div>';
  
  document.getElementById('lookup-results').innerHTML = html;
}

function closeLookupModal() {
  document.getElementById('lookup-modal').classList.remove('active');
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});
    </script>
</body>
</html>
    ''', drafts=drafts, event_count=event_count, healing_count=healing_count)

@app.route('/api/drafts/<draft_id>/approve', methods=['POST'])
def approve_draft(draft_id):
    """Approve a draft and mark it as approved."""
    try:
        drafts = load_drafts()
        for draft in drafts:
            if draft.get('id') == draft_id:
                draft['status'] = 'approved'
                draft['approved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_drafts(drafts)
                return jsonify({'ok': True, 'status': 'approved'})
        return jsonify({'error': 'Draft not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/reject', methods=['POST'])
def reject_draft(draft_id):
    """Reject a draft."""
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')
        
        drafts = load_drafts()
        for draft in drafts:
            if draft.get('id') == draft_id:
                draft['status'] = 'rejected'
                draft['rejected_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                draft['rejection_notes'] = notes
                save_drafts(drafts)
                return jsonify({'ok': True, 'status': 'rejected'})
        return jsonify({'error': 'Draft not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/escalate', methods=['POST'])
def escalate_draft(draft_id):
    """Escalate a draft to human review."""
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')
        to = data.get('to', 'cassie')
        
        drafts = load_drafts()
        for draft in drafts:
            if draft.get('id') == draft_id:
                draft['status'] = 'escalated'
                draft['escalated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                draft['escalation_notes'] = notes
                draft['escalated_to'] = to
                save_drafts(drafts)
                return jsonify({'ok': True, 'status': 'escalated'})
        return jsonify({'error': 'Draft not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/edit', methods=['POST'])
def edit_draft(draft_id):
    """Edit and approve a draft."""
    try:
        data = request.get_json() or {}
        draft_text = data.get('draft_text', '').strip()
        
        if not draft_text:
            return jsonify({'error': 'Draft text required'}), 400
        
        drafts = load_drafts()
        for draft in drafts:
            if draft.get('id') == draft_id:
                draft['draft_body'] = draft_text
                draft['status'] = 'approved'
                draft['edited_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                draft['approved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_drafts(drafts)
                return jsonify({'ok': True, 'status': 'edited_and_approved'})
        return jsonify({'error': 'Draft not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lookup', methods=['GET'])
def lookup_user():
    """Look up user across Kajabi, Eventbrite, and Klaviyo."""
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email parameter required'}), 400
    
    try:
        import requests
        import csv
        
        # API credentials
        EB_TOKEN = "NVPWHF7QOKK74KQ6ZF3W"
        EB_ORG_ID = "393488177349"
        KLAVIYO_API_KEY = "pk_8e0b3f093dfe5ae54a37b15fad3d2f513e"
        
        results = {
            'email': email,
            'kajabi': {'found': False, 'summary': 'API not available in dashboard mode'},
            'eventbrite': {'found': False, 'orders': [], 'summary': 'No orders found'},
            'klaviyo': {'found': False, 'summary': 'Not found'}
        }
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)