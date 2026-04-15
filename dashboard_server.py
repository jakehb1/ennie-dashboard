#!/usr/bin/env python3
"""
Ennie Support Dashboard — Railway deployment
All API keys via environment variables.
"""

import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

PORT = int(os.environ.get("PORT", 8899))

EB_TOKEN = os.environ.get("EB_TOKEN", "NVPWHF7QOKK74KQ6ZF3W")
EB_ORG_ID = os.environ.get("EB_ORG_ID", "393488177349")
KAJABI_CLIENT_ID = os.environ.get("KAJABI_CLIENT_ID", "d8nz6oBhB4JfTrFmYTy7VRTj")
KAJABI_CLIENT_SECRET = os.environ.get("KAJABI_CLIENT_SECRET", "Bok2Nb3WCSjGTYtZj2JLwuP7")
KLAVIYO_API_KEY = os.environ.get("KLAVIYO_API_KEY", "pk_8e0b3f093dfe5ae54a37b15fad3d2f513e")

# Kajabi token cache
_kajabi_token = {"token": None, "expires_at": 0}

# In-memory contact cache — loaded once on startup, refreshed every 6 hours
_contact_cache = {"contacts": [], "loaded_at": 0}

def load_contact_cache():
    import time
    now = time.time()
    if now - _contact_cache["loaded_at"] < 6 * 3600 and _contact_cache["contacts"]:
        return
    print("[cache] Loading Kajabi contacts into memory...")
    try:
        token = get_kajabi_token()
        headers = {"Authorization": f"Bearer {token}"}
        contacts = []
        page = 1
        while True:
            r = requests.get("https://api.kajabi.com/v1/contacts", headers=headers,
                             params={"page[size]": 200, "page[number]": page}, timeout=15)
            if not r.ok:
                break
            batch = r.json().get("data", [])
            if not batch:
                break
            for c in batch:
                attrs = c["attributes"]
                name = f"{attrs.get('first_name','')} {attrs.get('last_name','')}".strip()
                contacts.append({"name": name, "email": attrs.get("email", ""), "id": c["id"]})
            print(f"[cache] {len(contacts)} contacts loaded...")
            if len(batch) < 200:
                break
            page += 1
        _contact_cache["contacts"] = contacts
        _contact_cache["loaded_at"] = now
        print(f"[cache] Done — {len(contacts)} contacts cached")
    except Exception as e:
        print(f"[cache] Error loading contacts: {e}")

def get_kajabi_token():
    import time
    now = time.time()
    if not _kajabi_token["token"] or now >= _kajabi_token["expires_at"]:
        r = requests.post("https://api.kajabi.com/v1/oauth/token", json={
            "grant_type": "client_credentials",
            "client_id": KAJABI_CLIENT_ID,
            "client_secret": KAJABI_CLIENT_SECRET,
        }, timeout=10)
        r.raise_for_status()
        _kajabi_token["token"] = r.json()["access_token"]
        _kajabi_token["expires_at"] = now + (6 * 24 * 3600)
    return _kajabi_token["token"]


def search_kajabi_by_name(query: str) -> list:
    """Search cached contacts by name or email — instant after first load."""
    load_contact_cache()  # no-op if already loaded
    query_lower = query.lower().strip()
    results = []
    for c in _contact_cache["contacts"]:
        if query_lower in c["name"].lower() or query_lower in c["email"].lower():
            results.append({"name": c["name"], "email": c["email"]})
            if len(results) >= 10:
                break
    return results


def lookup_kajabi(email: str) -> dict:
    try:
        token = get_kajabi_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Search contacts
        r = requests.get("https://api.kajabi.com/v1/contacts", headers=headers,
                         params={"filter[email]": email, "page[size]": 20}, timeout=8)
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

        # Get offers
        offer_titles = []
        try:
            r2 = requests.get(f"https://app.kajabi.com/api/v1/contacts/{contact_id}/relationships/offers",
                              headers=headers, timeout=8)
            if r2.ok:
                # Get offer map
                offer_map = {}
                ro = requests.get("https://api.kajabi.com/v1/offers", headers=headers,
                                  params={"page[size]": 50}, timeout=8)
                if ro.ok:
                    for o in ro.json().get("data", []):
                        offer_map[o["id"]] = o.get("attributes", {}).get("title", "Unknown")
                offer_titles = [offer_map.get(o["id"], f"Offer #{o['id']}") for o in r2.json().get("data", [])]
        except Exception:
            pass

        # Customer record
        logins = ""
        last_active = ""
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
            "found": True,
            "name": name,
            "email": email,
            "contact_id": contact_id,
            "logins": logins,
            "last_active": last_active,
            "offers": offer_titles,
            "tags": attrs.get("tags", []),
        }
    except Exception as e:
        return {"found": False, "summary": f"Kajabi lookup error: {str(e)[:80]}"}


def lookup_eventbrite(email: str) -> dict:
    try:
        headers = {"Authorization": f"Bearer {EB_TOKEN}"}
        r = requests.get(
            f"https://www.eventbriteapi.com/v3/organizations/{EB_ORG_ID}/orders/",
            headers=headers,
            params={"only_emails": email, "expand": "event,attendees", "page_size": 20},
            timeout=10
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
                "event_name": event.get("name", {}).get("text", "Unknown event"),
                "event_date": event.get("start", {}).get("local", "")[:10],
                "order_id": order["id"],
                "status": order.get("status", "unknown"),
                "ticket_type": ", ".join(ticket_types) if ticket_types else "Unknown",
            })

        return {"found": bool(orders), "orders": orders, "summary": f"{len(orders)} order(s) found"}
    except Exception as e:
        return {"found": False, "orders": [], "summary": f"Eventbrite error: {str(e)[:80]}"}


def lookup_klaviyo(email: str) -> dict:
    try:
        headers = {"Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}", "revision": "2024-02-15"}
        r = requests.get("https://a.klaviyo.com/api/profiles/", headers=headers,
                         params={"filter": f'equals(email,"{email}")'}, timeout=8)
        if not r.ok or not r.json().get("data"):
            return {"found": False, "summary": "Not found in Klaviyo"}

        profile = r.json()["data"][0]
        pid = profile["id"]
        attrs = profile["attributes"]
        name = f"{attrs.get('first_name','')} {attrs.get('last_name','')}".strip()
        created = attrs.get("created", "")[:10]

        r2 = requests.get(f"https://a.klaviyo.com/api/profiles/{pid}/lists/", headers=headers, timeout=8)
        lists = [l.get("attributes", {}).get("name", "") for l in r2.json().get("data", [])] if r2.ok else []

        return {"found": True, "name": name, "created": created, "lists": lists}
    except Exception as e:
        return {"found": False, "summary": f"Klaviyo error: {str(e)[:80]}"}


HTML = open(os.path.join(os.path.dirname(__file__), "dashboard.html")).read()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/search":
            q = params.get("q", [""])[0].strip()
            if not q:
                self.send_json([])
                return
            results = search_kajabi_by_name(q)
            self.send_json(results)

        elif parsed.path == "/lookup":
            email = params.get("email", [""])[0].strip()
            query = params.get("q", [""])[0].strip()

            # If name given (not email), resolve to email first
            if not email and query and "@" not in query:
                matches = search_kajabi_by_name(query)
                if matches:
                    email = matches[0]["email"]
                else:
                    self.send_json({"error": f"No contact found for '{query}'"})
                    return
            elif not email and query:
                email = query

            if not email:
                self.send_json({"error": "No email or name provided"}, 400)
                return

            kajabi = lookup_kajabi(email)
            eventbrite = lookup_eventbrite(email)
            klaviyo = lookup_klaviyo(email)

            self.send_json({
                "email": email,
                "kajabi": kajabi,
                "eventbrite": eventbrite,
                "klaviyo": klaviyo,
            })
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    # Pre-load contact cache in background so first search is instant
    import threading
    threading.Thread(target=load_contact_cache, daemon=True).start()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Dashboard running on port {PORT}")
    server.serve_forever()
