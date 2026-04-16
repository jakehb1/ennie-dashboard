#!/usr/bin/env python3
"""
Ennie Support Dashboard v2 — Charlie Goldsmith Team
Flask + SQLite + Apple glassmorphism UI
"""

import os
import json
import sqlite3
import time
from functools import wraps

import requests
from flask import (Flask, render_template, request, session,
                   redirect, url_for, jsonify, g)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ennie-support-secret-2025")

DATABASE = os.environ.get("DATABASE_PATH", "/tmp/support.db")

# ── env vars ──────────────────────────────────────────────────────────────────
EB_TOKEN            = os.environ.get("EB_TOKEN",            "NVPWHF7QOKK74KQ6ZF3W")
EB_ORG_ID           = os.environ.get("EB_ORG_ID",           "393488177349")
KAJABI_CLIENT_ID    = os.environ.get("KAJABI_CLIENT_ID",    "d8nz6oBhB4JfTrFmYTy7VRTj")
KAJABI_CLIENT_SECRET= os.environ.get("KAJABI_CLIENT_SECRET","Bok2Nb3WCSjGTYtZj2JLwuP7")
KLAVIYO_API_KEY     = os.environ.get("KLAVIYO_API_KEY",     "pk_8e0b3f093dfe5ae54a37b15fad3d2f513e")

_kajabi_token = {"token": None, "expires_at": 0}


# ── Database ───────────────────────────────────────────────────────────────────
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL,
            name          TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id       TEXT UNIQUE,
            from_email      TEXT NOT NULL,
            from_name       TEXT,
            subject         TEXT NOT NULL,
            body_original   TEXT NOT NULL,
            draft_body      TEXT,
            classification  TEXT,
            escalate        BOOLEAN DEFAULT FALSE,
            kajabi_found    BOOLEAN DEFAULT FALSE,
            eventbrite_found BOOLEAN DEFAULT FALSE,
            status          TEXT DEFAULT 'pending',
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            reviewed_by     INTEGER,
            notes           TEXT
        );
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            topic      TEXT NOT NULL,
            question   TEXT NOT NULL,
            answer     TEXT NOT NULL,
            created_by INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS escalations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id      INTEGER,
            escalated_to  TEXT NOT NULL,
            notes         TEXT,
            response      TEXT,
            status        TEXT DEFAULT 'open',
            created_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (draft_id) REFERENCES drafts(id)
        );
    """)

    # Seed users
    seed_users = [
        ("Admin",    "admin@charliegoldsmith.com",    "admin123",    "admin"),
        ("Reviewer", "reviewer@charliegoldsmith.com", "reviewer123", "reviewer"),
        ("Cassie",   "cassie@charliegoldsmith.com",   "cassie123",   "cassie"),
        ("Charlie",  "charlie@charliegoldsmith.com",  "charlie123",  "charlie"),
    ]
    for name, email, password, role in seed_users:
        if not db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?,?,?,?)",
                (name, email, generate_password_hash(password), role),
            )

    # Seed demo drafts
    if db.execute("SELECT COUNT(*) FROM drafts").fetchone()[0] == 0:
        demos = [
            ("john@example.com",  "John Smith",    "Can't access my course",
             "Hi, I purchased the course last week but I can't log in. My email is john@example.com. Please help!",
             "account_access",
             "Hi John, thank you for reaching out! I've checked your account and it looks like your login is active. "
             "Please try resetting your password at our login page. Let me know if you need further help!"),
            ("sarah@test.com",    "Sarah Johnson", "Refund request",
             "I'd like to request a refund for my recent purchase. The course wasn't what I expected.",
             "refund",
             "Hi Sarah, I understand your frustration. I've reviewed your account and your purchase qualifies for a "
             "refund per our 30-day policy. I'll process this within 3–5 business days."),
            ("mike@domain.com",   "Mike Chen",     "Event registration question",
             "I registered for the upcoming workshop but didn't receive a confirmation email. Can you check?",
             "event",
             "Hi Mike, I've located your registration for the workshop. It looks like the confirmation went to your "
             "spam folder. I've resent it — please check!"),
            ("lisa@company.org",  "Lisa Park",     "Technical issue with video playback",
             "The videos in Module 3 keep buffering and won't play. I've tried different browsers.",
             "technical",
             "Hi Lisa, sorry to hear you're having trouble with Module 3. This is usually a browser cache issue. "
             "Please try clearing your cache or using an incognito window. Let me know if that helps!"),
        ]
        for from_email, from_name, subject, body, classification, draft_body in demos:
            thread_id = f"demo-{from_email.replace('@', '_').replace('.', '_')}"
            db.execute(
                "INSERT INTO drafts (thread_id,from_email,from_name,subject,body_original,draft_body,classification,status) "
                "VALUES (?,?,?,?,?,?,?,'pending')",
                (thread_id, from_email, from_name, subject, body, draft_body, classification),
            )

    db.commit()
    db.close()


# ── Auth helpers ───────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Lookup helpers (copied from dashboard_server.py) ──────────────────────────
def get_kajabi_token():
    now = time.time()
    if not _kajabi_token["token"] or now >= _kajabi_token["expires_at"]:
        r = requests.post(
            "https://api.kajabi.com/v1/oauth/token",
            json={"grant_type": "client_credentials",
                  "client_id": KAJABI_CLIENT_ID,
                  "client_secret": KAJABI_CLIENT_SECRET},
            timeout=10,
        )
        r.raise_for_status()
        _kajabi_token["token"] = r.json()["access_token"]
        _kajabi_token["expires_at"] = now + (6 * 24 * 3600)
    return _kajabi_token["token"]


def lookup_kajabi(email: str) -> dict:
    try:
        token = get_kajabi_token()
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            "https://api.kajabi.com/v1/contacts", headers=headers,
            params={"filter[email]": email, "page[size]": 20}, timeout=8,
        )
        if not r.ok:
            return {"found": False, "summary": f"Kajabi API error {r.status_code}"}
        contact = None
        for c in r.json().get("data", []):
            if c["attributes"].get("email", "").lower() == email.lower():
                contact = c
                break
        if not contact:
            return {"found": False, "summary": f"No Kajabi member found for {email}"}
        attrs = contact["attributes"]
        name = f"{attrs.get('first_name','')} {attrs.get('last_name','')}".strip()
        contact_id = contact["id"]
        offer_titles = []
        try:
            r2 = requests.get(
                f"https://app.kajabi.com/api/v1/contacts/{contact_id}/relationships/offers",
                headers=headers, timeout=8,
            )
            if r2.ok:
                offer_map = {}
                ro = requests.get(
                    "https://api.kajabi.com/v1/offers", headers=headers,
                    params={"page[size]": 50}, timeout=8,
                )
                if ro.ok:
                    for o in ro.json().get("data", []):
                        offer_map[o["id"]] = o.get("attributes", {}).get("title", "Unknown")
                offer_titles = [
                    offer_map.get(o["id"], f"Offer #{o['id']}")
                    for o in r2.json().get("data", [])
                ]
        except Exception:
            pass
        logins = last_active = ""
        customer_link = contact.get("links", {}).get("customer")
        if customer_link:
            try:
                rc = requests.get(customer_link, headers=headers, timeout=8)
                if rc.ok:
                    ca = rc.json().get("data", {}).get("attributes", {})
                    logins = str(ca.get("sign_in_count", ""))
                    last_active = (ca.get("last_request_at") or "")[:10]
            except Exception:
                pass
        return {
            "found": True, "name": name, "email": email, "contact_id": contact_id,
            "logins": logins, "last_active": last_active,
            "offers": offer_titles, "tags": attrs.get("tags", []),
        }
    except Exception as e:
        return {"found": False, "summary": f"Kajabi lookup error: {str(e)[:80]}"}


def lookup_eventbrite(email: str) -> dict:
    try:
        headers = {"Authorization": f"Bearer {EB_TOKEN}"}
        r = requests.get(
            f"https://www.eventbriteapi.com/v3/organizations/{EB_ORG_ID}/orders/",
            headers=headers,
            params={"only_emails": email, "expand": "event,attendees"},
            timeout=10,
        )
        if not r.ok:
            return {"found": False, "orders": [], "summary": f"Eventbrite error {r.status_code}"}
        orders = []
        for order in r.json().get("orders", []):
            if order.get("email", "").lower() != email.lower():
                continue
            event = order.get("event", {})
            attendees = order.get("attendees", [])
            ticket_types = list(set(a.get("ticket_class_name", "Unknown") for a in attendees))
            orders.append({
                "event_name":  event.get("name", {}).get("text", "Unknown event"),
                "event_date":  event.get("start", {}).get("local", "")[:10],
                "order_id":    order["id"],
                "status":      order.get("status", "unknown"),
                "ticket_type": ", ".join(ticket_types) if ticket_types else "Unknown",
            })
        return {"found": bool(orders), "orders": orders, "summary": f"{len(orders)} order(s) found"}
    except Exception as e:
        return {"found": False, "orders": [], "summary": f"Eventbrite error: {str(e)[:80]}"}


def lookup_klaviyo(email: str) -> dict:
    try:
        headers = {"Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}", "revision": "2024-02-15"}
        r = requests.get(
            "https://a.klaviyo.com/api/profiles/", headers=headers,
            params={"filter": f'equals(email,"{email}")'}, timeout=8,
        )
        if not r.ok or not r.json().get("data"):
            return {"found": False, "summary": "Not found in Klaviyo"}
        profile = r.json()["data"][0]
        pid   = profile["id"]
        attrs = profile["attributes"]
        name  = f"{attrs.get('first_name','')} {attrs.get('last_name','')}".strip()
        created = attrs.get("created", "")[:10]
        r2 = requests.get(
            f"https://a.klaviyo.com/api/profiles/{pid}/lists/",
            headers=headers, timeout=8,
        )
        lists = [
            l.get("attributes", {}).get("name", "")
            for l in r2.json().get("data", [])
        ] if r2.ok else []
        return {"found": True, "name": name, "created": created, "lists": lists}
    except Exception as e:
        return {"found": False, "summary": f"Klaviyo error: {str(e)[:80]}"}


# ── Page routes ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    role = session.get("role")
    if role == "charlie":
        return redirect(url_for("charlie"))
    if role == "cassie":
        return redirect(url_for("escalations"))
    return redirect(url_for("inbox"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"]    = user["role"]
            session["name"]    = user["name"]
            session["email"]   = user["email"]
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid email or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/inbox")
@login_required
def inbox():
    db = get_db()
    drafts = db.execute("""
        SELECT d.*, u.name AS reviewer_name
        FROM drafts d
        LEFT JOIN users u ON d.reviewed_by = u.id
        WHERE d.status = 'pending'
        ORDER BY d.created_at DESC
    """).fetchall()
    return render_template("inbox.html", drafts=drafts)


@app.route("/lookup")
@login_required
def lookup():
    return render_template("lookup.html")


@app.route("/escalations")
@role_required("cassie", "admin")
def escalations():
    db = get_db()
    items = db.execute("""
        SELECT e.*, d.from_email, d.from_name, d.subject, d.body, d.classification
        FROM escalations e
        JOIN drafts d ON e.draft_id = d.id
        WHERE e.escalated_to = 'cassie' AND e.status = 'open'
        ORDER BY e.created_at DESC
    """).fetchall()
    return render_template("escalations.html", escalations=items)


@app.route("/knowledge_base")
@role_required("cassie", "admin")
def knowledge_base():
    db = get_db()
    entries = db.execute("""
        SELECT kb.*, u.name AS author
        FROM knowledge_base kb
        LEFT JOIN users u ON kb.created_by = u.id
        ORDER BY kb.topic, kb.created_at DESC
    """).fetchall()
    topics = list(dict.fromkeys(e["topic"] for e in entries))
    return render_template("knowledge_base.html", entries=entries, topics=topics)


@app.route("/charlie")
@role_required("charlie", "admin")
def charlie():
    db = get_db()
    items = db.execute("""
        SELECT e.*, d.from_email, d.from_name, d.subject, d.body, d.classification
        FROM escalations e
        JOIN drafts d ON e.draft_id = d.id
        WHERE e.escalated_to = 'charlie' AND e.status = 'open'
        ORDER BY e.created_at DESC
    """).fetchall()
    return render_template("charlie.html", escalations=items)


# ── API ────────────────────────────────────────────────────────────────────────
@app.route("/api/drafts/<int:draft_id>/approve", methods=["POST"])
@login_required
def api_approve(draft_id):
    data = request.get_json() or {}
    db = get_db()
    draft = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    if not draft:
        return jsonify({"error": "Not found"}), 404

    # Allow editing the draft body before sending
    final_body = data.get("draft_body", draft["draft_body"])

    db.execute("UPDATE drafts SET status='approved', reviewed_by=?, draft_body=? WHERE id=?",
               (session["user_id"], final_body, draft_id))
    db.commit()

    # Fire webhook to local poller to actually send the email
    send_webhook = os.environ.get("SEND_WEBHOOK_URL", "")
    send_webhook_key = os.environ.get("SEND_WEBHOOK_KEY", "ennie-send-2025")
    if send_webhook:
        try:
            import requests as _req
            _req.post(send_webhook, headers={"X-API-Key": send_webhook_key},
                json={
                    "action": "send",
                    "thread_id": draft["thread_id"],
                    "to_email": draft["from_email"],
                    "to_name": draft["from_name"],
                    "subject": draft["subject"],
                    "body": final_body,
                }, timeout=10)
        except Exception:
            pass  # Don't block approval if webhook fails

    return jsonify({"ok": True})


@app.route("/api/drafts/<int:draft_id>/reject", methods=["POST"])
@login_required
def api_reject(draft_id):
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE drafts SET status='rejected', reviewed_by=?, notes=? WHERE id=?",
               (session["user_id"], data.get("notes", ""), draft_id))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/drafts/<int:draft_id>/escalate", methods=["POST"])
@login_required
def api_escalate(draft_id):
    data   = request.get_json() or {}
    target = data.get("to", "cassie")
    notes  = data.get("notes", "")
    db = get_db()
    db.execute("UPDATE drafts SET status='escalated', reviewed_by=? WHERE id=?",
               (session["user_id"], draft_id))
    db.execute("INSERT INTO escalations (draft_id, escalated_to, notes) VALUES (?,?,?)",
               (draft_id, target, notes))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/drafts/<int:draft_id>/edit", methods=["POST"])
@login_required
def api_edit(draft_id):
    data = request.get_json() or {}
    db = get_db()
    db.execute(
        "UPDATE drafts SET draft_body=?, status='approved', reviewed_by=? WHERE id=?",
        (data.get("draft_body", ""), session["user_id"], draft_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/escalations/<int:esc_id>/respond", methods=["POST"])
@role_required("cassie", "charlie", "admin")
def api_escalation_respond(esc_id):
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE escalations SET response=?, status='resolved' WHERE id=?",
               (data.get("response", ""), esc_id))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/escalations/<int:esc_id>/escalate-to-charlie", methods=["POST"])
@role_required("cassie", "admin")
def api_escalate_to_charlie(esc_id):
    data  = request.get_json() or {}
    notes = data.get("notes", "")
    db    = get_db()
    esc   = db.execute("SELECT draft_id FROM escalations WHERE id=?", (esc_id,)).fetchone()
    if esc:
        db.execute("UPDATE escalations SET status='escalated_up' WHERE id=?", (esc_id,))
        db.execute(
            "INSERT INTO escalations (draft_id, escalated_to, notes) VALUES (?,?,?)",
            (esc["draft_id"], "charlie", notes),
        )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/lookup")
@login_required
def api_lookup():
    email = request.args.get("email", "").strip()
    if not email:
        return jsonify({"error": "No email provided"}), 400
    return jsonify({
        "email":      email,
        "kajabi":     lookup_kajabi(email),
        "eventbrite": lookup_eventbrite(email),
        "klaviyo":    lookup_klaviyo(email),
    })


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    """Receive a draft from the local poller. Protected by API key."""
    api_key = request.headers.get("X-API-Key", "")
    expected = os.environ.get("INGEST_API_KEY", "ennie-ingest-2025")
    if api_key != expected:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    required = ["thread_id", "from_email", "from_name", "subject", "body_original", "draft_body", "classification"]
    if not all(data.get(k) for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    db = get_db()

    # Upsert — update if thread already exists
    existing = db.execute("SELECT id FROM drafts WHERE thread_id=?", (data["thread_id"],)).fetchone()
    if existing:
        db.execute("""
            UPDATE drafts SET draft_body=?, classification=?, escalate=?, updated_at=datetime('now')
            WHERE thread_id=?
        """, (data["draft_body"], data["classification"], data.get("escalate", False), data["thread_id"]))
    else:
        db.execute("""
            INSERT INTO drafts (thread_id, from_email, from_name, subject, body_original, draft_body,
                                classification, escalate, kajabi_found, eventbrite_found, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,'pending')
        """, (
            data["thread_id"], data["from_email"], data["from_name"],
            data["subject"], data["body_original"], data["draft_body"],
            data["classification"], data.get("escalate", False),
            data.get("kajabi_found", False), data.get("eventbrite_found", False),
        ))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/approved-drafts")
def api_approved_drafts():
    """Returns drafts approved but not yet sent — for the local poller to send."""
    api_key = request.headers.get("X-API-Key", "")
    if api_key != os.environ.get("INGEST_API_KEY", "ennie-ingest-2025"):
        return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    drafts = db.execute(
        "SELECT * FROM drafts WHERE status='approved' ORDER BY updated_at ASC"
    ).fetchall()
    return jsonify([dict(d) for d in drafts])


@app.route("/api/drafts/<int:draft_id>/mark-sent", methods=["POST"])
def api_mark_sent(draft_id):
    api_key = request.headers.get("X-API-Key", "")
    if api_key != os.environ.get("INGEST_API_KEY", "ennie-ingest-2025"):
        return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    db.execute("UPDATE drafts SET status='sent', updated_at=datetime('now') WHERE id=?", (draft_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/kb", methods=["GET"])
@login_required
def api_kb_get():
    db      = get_db()
    entries = db.execute("SELECT * FROM knowledge_base ORDER BY topic, created_at DESC").fetchall()
    return jsonify([dict(e) for e in entries])


@app.route("/api/kb", methods=["POST"])
@role_required("cassie", "admin")
def api_kb_post():
    data     = request.get_json() or {}
    topic    = data.get("topic",    "").strip()
    question = data.get("question", "").strip()
    answer   = data.get("answer",   "").strip()
    if not all([topic, question, answer]):
        return jsonify({"error": "topic, question, answer required"}), 400
    db  = get_db()
    cur = db.execute(
        "INSERT INTO knowledge_base (topic, question, answer, created_by) VALUES (?,?,?,?)",
        (topic, question, answer, session["user_id"]),
    )
    db.commit()
    return jsonify({"ok": True, "id": cur.lastrowid})


@app.route("/api/kb/<int:entry_id>", methods=["PUT"])
@role_required("cassie", "admin")
def api_kb_update(entry_id):
    data = request.get_json() or {}
    db   = get_db()
    db.execute(
        "UPDATE knowledge_base SET topic=?, question=?, answer=? WHERE id=?",
        (data.get("topic"), data.get("question"), data.get("answer"), entry_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/kb/<int:entry_id>", methods=["DELETE"])
@role_required("cassie", "admin")
def api_kb_delete(entry_id):
    db = get_db()
    db.execute("DELETE FROM knowledge_base WHERE id=?", (entry_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/admin/reset-db")
def admin_reset_db():
    """Reset and re-seed the DB. Protected by env var."""
    secret = request.args.get("secret", "")
    if secret != os.environ.get("RESET_SECRET", "ennie-reset-2025"):
        return "Unauthorized", 403
    import os as _os
    try:
        _os.remove(DATABASE)
    except Exception:
        pass
    init_db()
    return "DB reset and re-seeded. <a href='/login'>Login</a>"


# ── Entrypoint ─────────────────────────────────────────────────────────────────
@app.route("/admin/sql-exec")
def sql_exec():
    """Execute raw SQL - REMOVE IN PRODUCTION"""
    sql = request.args.get('sql', '')
    if not sql:
        return "Usage: /admin/sql-exec?sql=INSERT..."
    
    try:
        db = get_db()
        db.execute(sql)
        db.commit()
        return f"Success: {sql[:100]}..."
    except Exception as e:
        return f"Error: {e}"


@app.route("/admin/add-real-data")
def add_real_data():
    """Manually add real support data - remove after testing."""
    db = get_db()
    
    # Linda Edwards - real email from today
    db.execute("""
        INSERT INTO drafts (thread_id, from_email, from_name, subject, body_original, draft_body, classification, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (
        "real-linda-edwards-20260416",
        "alushlifetravel@yahoo.com",
        "Linda Edwards",
        "Re: Energy Teaching: Q&A Session #2 ✨",
        "Hello,Was there a teaching marathon this week? I don't have it scheduled and only have the 3:00 healing session for Saturday at this time on my calendar. Is it possible to get a schedule for at least",
        "Hi Linda,\n\nThank you for your question about this week's schedule. The regular teaching marathon wasn't scheduled this week, so you're seeing the correct calendar with just the 3:00 PM healing session on Saturday.\n\nFor future scheduling updates, we recommend checking our main calendar or email announcements.\n\nBest regards,\nCharlie Goldsmith Support Team",
        "event_question"
    ))
    
    # Add a few more real examples
    real_drafts = [
        ("real-pamela-hillman-podcast", "pamelahillman88@gmail.com", "Pamela Hillman", 
         "Podcast Guest Inquiry - This is Healing", 
         "Hello. Who would I contact to invite Charlie to be a guest on a podcast? It's called This is Healing. On Spotify and Apple.",
         "Hi Pamela,\n\nThank you for your interest in having Charlie as a guest on This is Healing podcast. I've forwarded your request to our media team who will be in touch shortly.\n\nBest regards,\nCharlie Goldsmith Support Team",
         "media_podcast_inquiry"),
        ("real-danielle-stokes-healing", "daniellestokes2004@yahoo.com", "Danielle Stokes",
         "Hoping Charlie can work on me",
         "Hi Casey, I am hoping Charlie can work on me. I accidentally ate almonds and drank juices with coconut water and have symptoms.",
         "Hi Danielle,\n\nThank you for reaching out. For individual healing sessions, please visit our booking page. You can also join our group healing sessions which happen regularly.\n\nBest regards,\nCharlie Goldsmith Support Team",
         "one_on_one_healing_request_medical_context")
    ]
    
    for thread_id, email, name, subject, body, draft, classification in real_drafts:
        db.execute("""
            INSERT INTO drafts (thread_id, from_email, from_name, subject, body_original, draft_body, classification, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (thread_id, email, name, subject, body, draft, classification))
    
    db.commit()
    return f"Added Linda Edwards + {len(real_drafts)} real support drafts. <a href='/login'>View Dashboard</a>"


@app.route("/debug")
def debug_info():
    """Surface any startup errors — remove before production use."""
    import sys, traceback
    info = {
        "python": sys.version,
        "database": DATABASE,
        "db_exists": os.path.exists(DATABASE),
        "env_keys": [k for k in os.environ if not k.lower().startswith('secret')],
    }
    try:
        db = get_db()
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        info["tables"] = [t[0] for t in tables]
        info["db_ok"] = True
    except Exception as e:
        info["db_error"] = str(e)
        info["db_ok"] = False
    return jsonify(info)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
