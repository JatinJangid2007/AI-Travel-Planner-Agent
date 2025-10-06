from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import datetime
from agent import TravelPlannerAgent
from firebase import FirebaseHelper

load_dotenv()

app = Flask(__name__)
CORS(app)

firebase = FirebaseHelper()
agent = TravelPlannerAgent()

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "AI Travel Planner Agent",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "POST /plan": "Create a travel plan from natural language query",
            "GET /history": "Get user's past travel plans",
            "GET /health": "Health check endpoint",
            "GET /demo": "Interactive demo UI"
        },
        "example_request": {
            "endpoint": "/plan",
            "method": "POST",
            "body": {
                "uid": "user-123",
                "query": "I want to go from Dubai to Istanbul from Nov 10 to Nov 15"
            }
        },
        "documentation": "See README.md for full API documentation"
    })

@app.route('/demo', methods=['GET'])
def demo():
    """Serve the demo UI"""
    return send_from_directory('static', 'demo.html')

@app.route('/health', methods=['GET'])
def health():
    try:
        firebase_status = "connected" if firebase.db else "disconnected"
        agent_status = "ready" if agent.llm else "not initialized"
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "services": {
                "firebase": firebase_status,
                "agent": agent_status,
                "api": "running"
            },
            "version": "1.0.0"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 500

@app.route('/plan', methods=['POST'])
def create_plan():
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'query' in request body",
                "message": "Please provide a travel query. Example: 'I want to go from Dubai to Istanbul from Nov 10 to Nov 15'"
            }), 400
        
        uid = data.get('uid')
        id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if id_token and not uid:
            decoded_token = firebase.verify_token(id_token)
            if decoded_token:
                uid = decoded_token['uid']
            else:
                return jsonify({
                    "success": False,
                    "error": "Invalid authentication token",
                    "message": "Please provide a valid Firebase ID token"
                }), 401
        
        if not uid:
            uid = "demo-user"
        
        firebase.get_or_create_user(uid)
        
        # Run agent
        query = data['query']
        print(f"Processing query for user {uid}: {query}")
        
        result = agent.run(query)
        
        # Add status to each step
        for step in result.get('steps', []):
            if 'status' not in step:
                step['status'] = 'success' if step.get('output') else 'failed'
        
        # Save to Firestore
        plan_id = firebase.save_plan(
            uid=uid,
            query=query,
            plan=result.get('plan', {}),
            steps=result.get('steps', [])
        )
        
        # Return comprehensive response
        response = {
            "success": True,
            "plan_id": plan_id,
            "query": query,
            "plan": result.get('plan', {}),
            "steps": result.get('steps', []),
            "summary": result.get('plan', {}).get('summary', ''),
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "tools_used": [step['tool'] for step in result.get('steps', [])],
            "debug_info": {
                "total_steps": len(result.get('steps', [])),
                "successful_tools": len([s for s in result.get('steps', []) if s.get('status') == 'success']),
                "failed_tools": len([s for s in result.get('steps', []) if s.get('status') == 'failed'])
            }
        }
        
        print(f"Successfully created plan {plan_id} for user {uid}")
        return jsonify(response), 200
    
    except Exception as e:
        print(f"Error creating plan: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "An error occurred while creating your travel plan. Please try again.",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 500

@app.route('/history', methods=['GET'])
def get_history():
    try:
        limit = min(int(request.args.get('limit', 10)), 50)  # Max 50
        id_token = request.headers.get('Authorization', '').replace('Bearer ', '')

        # Require token unless it's demo
        if not id_token:
            return jsonify({
                "success": False,
                "error": "Authentication required",
                "message": "Please provide a valid Firebase ID token"
            }), 401

        # Verify token
        decoded_token = firebase.verify_token(id_token)
        if not decoded_token:
            return jsonify({
                "success": False,
                "error": "Invalid authentication token",
                "message": "Please provide a valid Firebase ID token"
            }), 401

        uid = decoded_token['uid']

        # Special case: demo user (public access without login)
        if uid == "demo-user":
            history = firebase.get_user_history("demo-user", limit=limit)
        else:
            history = firebase.get_user_history(uid, limit=limit)

        # Enhance history with summary info
        enhanced_history = []
        for item in history:
            enhanced_item = {
                "id": item.get('id'),
                "query": item.get('query'),
                "plan": item.get('plan', {}),
                "steps": item.get('steps', []),
                "createdAt": item.get('createdAt'),
                "destination": item.get('plan', {}).get('destination', 'Unknown'),
                "origin": item.get('plan', {}).get('origin', 'Unknown'),
                "duration_days": item.get('plan', {}).get('duration_days', 0),
                "tools_used": len(item.get('steps', []))
            }
            enhanced_history.append(enhanced_item)

        return jsonify({
            "success": True,
            "uid": uid,
            "history": enhanced_history,
            "total": len(enhanced_history),
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200

    except Exception as e:
        print(f"Error fetching history: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "An error occurred while fetching your history",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('ENVIRONMENT') != 'production')