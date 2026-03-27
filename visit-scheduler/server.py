from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='.', static_url_path='')
# Enable CORS for the frontend
CORS(app)

# Store API credentials (you can switch these to env vars later)
KAKAO_JS_KEY = os.environ.get('KAKAO_JS_KEY', 'd83678527e52f4d753df486ac01f7d0c')
KAKAO_REST_KEY = os.environ.get('KAKAO_REST_KEY', '007cb32ee7d003fec1bd6fc308b7ece7')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/directions', methods=['GET'])
def get_directions():
    origin = request.args.get('start') # "lng,lat"
    destination = request.args.get('goal') # "lng,lat"
    waypoints = request.args.get('waypoints') # "lng,lat|lng,lat"
    
    # REST API Key should be passed in headers
    client_secret = request.headers.get('X-NCP-APIGW-API-KEY', KAKAO_REST_KEY)

    if not origin or not destination:
        return jsonify({'error': 'start and goal are required'}), 400

    # Kakao Mobility Directions API
    url = 'https://apis-navi.kakaomobility.com/v1/directions'
    
    # Kakao uses '|' for waypoints, same as Naver, but param name is 'waypoints'
    params = {
        'origin': origin,
        'destination': destination,
        'priority': 'RECOMMEND'
    }
    
    if waypoints:
        params['waypoints'] = waypoints

    headers = {
        'Authorization': f'KakaoAK {client_secret}'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_places():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'query is required'}), 400

    client_secret = request.headers.get('X-NCP-APIGW-API-KEY', KAKAO_REST_KEY)
    print(f"DEBUG: Search query received: {query}")
    print(f"DEBUG: Using REST API Key: {client_secret[:5]}...")

    # Kakao Local Search (Keyword)
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    params = {'query': query}
    headers = {
        'Authorization': f'KakaoAK {client_secret}'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"DEBUG: Kakao Status Code: {response.status_code}")
        kakao_data = response.json()
        if response.status_code != 200:
            print(f"DEBUG: Kakao Error Response: {kakao_data}")
        return jsonify(kakao_data), response.status_code
    except Exception as e:
        print(f"DEBUG: Search Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Visit Scheduler API Proxy Server on http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
