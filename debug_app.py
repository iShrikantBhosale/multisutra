#!/usr/bin/env python3
"""
Minimal debug version of the Flask app to identify deployment issues.
This version removes database dependencies to isolate the problem.
"""

import os
from flask import Flask, jsonify
from datetime import datetime

def create_debug_app():
    """Create a minimal Flask app for debugging"""
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'debug-key')
    
    @app.route('/')
    def index():
        return jsonify({
            'status': 'MultiSutra CMS Debug Mode',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': os.environ.get('FLASK_ENV', 'unknown'),
            'port': os.environ.get('PORT', '8000'),
            'database_url': 'CONFIGURED' if os.environ.get('DATABASE_URL') else 'MISSING'
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'multisutra-debug'
        })
    
    @app.route('/env')
    def env_check():
        """Show environment variables (excluding secrets)"""
        env_vars = {}
        for key, value in os.environ.items():
            if 'SECRET' not in key.upper() and 'PASSWORD' not in key.upper() and 'TOKEN' not in key.upper():
                env_vars[key] = value[:50] + '...' if len(value) > 50 else value
        
        return jsonify({
            'environment_variables': env_vars,
            'total_vars': len(os.environ)
        })
    
    return app

# Create app instance for production
app = create_debug_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)