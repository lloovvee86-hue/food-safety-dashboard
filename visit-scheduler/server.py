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
    
    try:
        kw_res = requests.get(keyword_url, params={'query': query}, headers=headers)
        kw_data = kw_res.json()
        
        # 2. Try Address Search as fallback or addition
        addr_url = 'https://dapi.kakao.com/v2/local/search/address.json'
        ad_res = requests.get(addr_url, params={'query': query}, headers=headers)
        ad_data = ad_res.json()
        
        # Merge results
        documents = kw_data.get('documents', [])
        
        # Convert address results to match keyword format
        for ad in ad_data.get('documents', []):
            # Check if already in keyword results (by coordinate)
            if any(d['x'] == ad['x'] and d['y'] == ad['y'] for d in documents):
                continue
                
            documents.append({
                'place_name': ad.get('address_name'),
                'address_name': ad.get('address_name'),
                'road_address_name': ad.get('road_address', {}).get('address_name', ''),
                'x': ad.get('x'),
                'y': ad.get('y'),
                'category_group_name': '주소/건물'
            })
            
        # 3. Business Suffix Fallback (if still no results)
        if not documents:
            first_word = query.split()[0]
            suffixes = ['공장', '본사', '지점', '사무소', '연구소', '물류']
            for suffix in suffixes:
                if len(documents) >= 5: break
                s_query = f"{first_word} {suffix}"
                s_res = requests.get(keyword_url, params={'query': s_query}, headers=headers)
                s_data = s_res.json()
                
                other_parts = query.split()[1:]
                for doc in s_data.get('documents', []):
                    full_text = (doc['place_name'] + ' ' + doc['address_name'] + ' ' + doc.get('road_address_name', '')).lower()
                    if all(p.lower() in full_text for p in other_parts):
                        if not any(d['x'] == doc['x'] and d['y'] == doc['y'] for d in documents):
                            documents.append(doc)

        return jsonify({'documents': documents, 'meta': {'total_count': len(documents)}}), 200
        
    except Exception as e:
        print(f"DEBUG: Search Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Visit Scheduler API Proxy Server on http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
