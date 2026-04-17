#!/usr/bin/env python3
"""
Minimal test version to debug Railway deployment
"""

from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Minimal test app is working!"

@app.route('/api/test')
def api_test():
    return jsonify({
        'status': 'working',
        'port': os.environ.get('PORT', 'not set'),
        'message': 'API routes are functional'
    })

@app.route('/api/drafts', methods=['GET'])
def get_drafts_minimal():
    return jsonify([{
        'id': 'test-123',
        'from_name': 'Test User',
        'subject': 'Test Draft',
        'status': 'pending'
    }])

print("Minimal app starting...")
print(f"PORT: {os.environ.get('PORT', 'not set')}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)