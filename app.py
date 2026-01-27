import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

app = Flask(__name__)
app.secret_key = "frail_app_key"

# --- 設定 ---
CLIENT_CONFIG = {
    "web": {
        "client_id": "734131799600-cn8qec6q6dqh24v93bf4ubabb0gtjm5d.apps.googleusercontent.com",
        "client_secret": "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",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        # ★ここを Render の URL + /callback に固定する！
        "redirect_uris": ["https://frail-system.onrender.com/callback"]
    }
}
SCOPES = ['https://www.googleapis.com/auth/drive.file']

@app.route('/')
def index():
    if 'credentials' not in session:
        return '<div style="text-align:center;margin-top:100px;"><h1>フレイル測定</h1><a href="/login"><button style="padding:20px;font-size:20px;cursor:pointer;">Googleでログイン</button></a></div>'
    return render_template('index.html')

@app.route('/login')
def login():
    # ★ここも確実に Render の URL を使うように指定
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = "https://frail-system.onrender.com/callback"
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/callback')
def callback():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = "https://frail-system.onrender.com/callback"
    flow.fetch_token(code=request.args.get('code'))
    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token, 'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri, 'client_id': creds.client_id,
        'client_secret': creds.client_secret, 'scopes': creds.scopes
    }
    return redirect(url_for('index'))

@app.route('/save', methods=['POST'])
def save():
    if 'credentials' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    try:
        data = request.json
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        
        filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_body = "item,value\n" + "\n".join([f"{k},{v}" for k, v in data.items() if k != 'is_done'])
        media = MediaInMemoryUpload(csv_body.encode('utf-8-sig'), mimetype='text/csv')
        
        service.files().create(body={'name': filename}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Renderでは環境変数 PORT が使われるため
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)