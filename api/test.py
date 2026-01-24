"""
Simple test endpoint for Vercel
"""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
@app.route('/api/test')
def test():
    return jsonify({"message": "Hello from Vercel!", "status": "working"})
