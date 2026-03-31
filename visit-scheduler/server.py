import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
# Enable CORS for the frontend
CORS(app)

# Store API credentials (you can switch these to env vars later)
KAKAO_JS_KEY = os.environ.get('KAKAO_JS_KEY', 'd83678527e52f4d753df486ac01f7d0c')
KAKAO_REST_KEY = os.environ.get('KAKAO_REST_KEY', '007cb32ee7d003fec1bd6fc308b7ece7')


# File paths
BASE_ENT_FILE = 'enterprise_directory.json'
CUSTOM_ENT_FILE = 'custom_enterprise.json'

# Initialize custom directory if not exists
if not os.path.exists(CUSTOM_ENT_FILE):
    with open(CUSTOM_ENT_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

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

@app.route('/api/enterprise/list', methods=['GET'])
def list_enterprise():
    try:
        base_data = []
        if os.path.exists(BASE_ENT_FILE):
            with open(BASE_ENT_FILE, 'r', encoding='utf-8') as f:
                base_data = json.load(f)
        
        custom_data = []
        if os.path.exists(CUSTOM_ENT_FILE):
            with open(CUSTOM_ENT_FILE, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)
        
        # Merge lists, avoiding duplicates if necessary (using name+address as key)
        seen = set()
        merged = []
        
        for item in base_data + custom_data:
            key = f"{item.get('name')}|{item.get('address')}"
            if key not in seen:
                seen.add(key)
                merged.append(item)
                
        return jsonify({'documents': merged, 'custom_count': len(custom_data)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/enterprise/add', methods=['POST'])
def add_enterprise():
    try:
        new_entry = request.json
        if not new_entry or 'name' not in new_entry or 'address' not in new_entry:
            return jsonify({'error': 'Invalid data'}), 400
        
        custom_data = []
        if os.path.exists(CUSTOM_ENT_FILE):
            with open(CUSTOM_ENT_FILE, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)
        
        # Check for duplication
        exists = any(e['name'] == new_entry['name'] and e['address'] == new_entry['address'] for e in custom_data)
        if not exists:
            custom_data.append(new_entry)
            with open(CUSTOM_ENT_FILE, 'w', encoding='utf-8') as f:
                json.dump(custom_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'status': 'success', 'count': len(custom_data)}), 200
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

    # 1. Try Keyword Search first
    keyword_url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    headers = {'Authorization': f'KakaoAK {client_secret}'}
    
    documents = []
    try:
        kw_res = requests.get(keyword_url, params={'query': query}, headers=headers)
        print(f"DEBUG: Keyword search status: {kw_res.status_code}")
        if kw_res.status_code == 200:
            kw_data = kw_res.json()
            documents.extend(kw_data.get('documents', []))
            print(f"DEBUG: Keyword search found {len(kw_data.get('documents', []))} results")
        else:
            print(f"DEBUG: Keyword search failed: {kw_res.text}")
        
        # 2. Try Address Search fallback (Especially for specific addresses like 'Migeum-ro 114')
        addr_url = 'https://dapi.kakao.com/v2/local/search/address.json'
        ad_res = requests.get(addr_url, params={'query': query}, headers=headers)
        print(f"DEBUG: Address search status: {ad_res.status_code}")
        if ad_res.status_code == 200:
            ad_data = ad_res.json()
            ad_docs = ad_data.get('documents', [])
            print(f"DEBUG: Address search found {len(ad_docs)} results")
            for ad in ad_docs:
                # Coordinate-based de-duplication to avoid messy results
                is_duplicate = any(abs(float(d.get('x', 0)) - float(ad.get('x', 0))) < 0.0001 and 
                                 abs(float(d.get('y', 0)) - float(ad.get('y', 0))) < 0.0001 for d in documents)
                if not is_duplicate:
                    documents.append({
                        'place_name': ad.get('address_name'),
                        'address_name': ad.get('address_name'),
                        'road_address_name': ad.get('road_address', {}).get('address_name', '') if ad.get('road_address') else '',
                        'x': ad.get('x'),
                        'y': ad.get('y'),
                        'category_group_name': '주소/건물'
                    })
        else:
            print(f"DEBUG: Address search failed: {ad_res.text}")
            
        print(f"DEBUG: Total documents being returned: {len(documents)}")
        return jsonify({'documents': documents, 'meta': {'total_count': len(documents)}}), 200
        
    except Exception as e:
        print(f"DEBUG: Search Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Visit Scheduler API Proxy Server on http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
