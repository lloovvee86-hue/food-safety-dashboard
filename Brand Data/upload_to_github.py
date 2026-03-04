import requests
import base64
import json
import os

TOKEN = "YOUR_GITHUB_TOKEN_HERE"
REPO = "lloovvee86-hue/food-safety-dashboard"
BRANCH = "main"

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def upload_file(file_path, repo_path, commit_message):
    print(f"Uploading {file_path} to {repo_path}...")
    
    # Get current file SHA to update it (required by GitHub API if file exists)
    url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}?ref={BRANCH}"
    response = requests.get(url, headers=headers)
    
    sha = None
    if response.status_code == 200:
        sha = response.json().get('sha')
        print(f"File exists. SHA: {sha}")
    elif response.status_code == 404:
        print("File does not exist yet. Will create a new one.")
    else:
        print(f"Error checking file status: {response.status_code} {response.text}")
        return

    # Read the file
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read local file {file_path}: {e}")
        return

    # Base64 encode the content
    content_b64 = base64.b64encode(content).decode('utf-8')

    # Prepare data
    data = {"message": commit_message, "content": content_b64, "branch": BRANCH}
    if sha:
        data["sha"] = sha

    # Put to create/update
    put_url = f"https://api.github.com/repos/{REPO}/contents/{repo_path}"
    put_response = requests.put(put_url, headers=headers, data=json.dumps(data))

    if put_response.status_code in [200, 201]:
        print(f"Successfully uploaded {repo_path}")
    else:
        print(f"Failed to upload {repo_path}: {put_response.status_code} {put_response.text}")

if __name__ == "__main__":
    upload_file(r"d:\풀무원\Antigravity\index.html", "index.html", "[봇] 대시보드 날짜 인터페이스 최신화 업데이트 (수동적용)")
    upload_file(r"d:\풀무원\Antigravity\food_data.csv", "food_data.csv", "[봇] 113건 최신 데이터 반영 (수동적용)")
    print("Done!")
