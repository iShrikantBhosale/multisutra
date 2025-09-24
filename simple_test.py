#!/usr/bin/env python3
"""
Ultra-minimal Flask app to test if basic deployment works.
This removes all complexity to isolate the 502 error.
"""

from flask import Flask, jsonify
import os

# Create the simplest possible Flask app
app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        'status': 'MultiSutra CMS is alive!',
        'port': os.environ.get('PORT', 'not set'),
        'message': 'Basic Flask app is working'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)