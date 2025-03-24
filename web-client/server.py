from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import os
import sys

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/process', methods=['POST'])
def process_query():
    data = request.json
    query = data.get('query')
    history = data.get('history', [])
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # Reference the original server.py in the parent directory
        original_server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
        
        # Construct command
        cmd = ['uv', 'run', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'streamlit_client.py'), original_server_path, query]
        
        # Add conversation history if available
        if history:
            history_json = json.dumps(history)
            cmd.append('--history')
            cmd.append(history_json)
        
        # Execute command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            return jsonify({'error': f"Command failed with code {process.returncode}", 'details': stderr}), 500
        
        # Extract response from output
        response = stdout
        if "\nResponse:" in response:
            response = response.split("\nResponse:", 1)[1].strip()
        
        return jsonify({'message': response})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 