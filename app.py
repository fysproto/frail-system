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
        "redirect_uris": ["https://frail-system.onrender.com/callback"]
    }
}
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- ルート：マイページ ---
@app.route('/')
def index():
    if 'credentials' not in session:
        # ログイン前：大きなボタンのトップページ
        return '''
        <html>
        <head><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;}
        button{padding:20px 40px;font-size:1.5rem;cursor:pointer;background:#007bff;color:white;border:none;border-radius:12px;box-shadow:0 4px 10px rgba(0,0,0,0.1);}</style></head>
        <body><h1>フレイル測定アプリ</h1><a href="/login"><button>Googleでログイン</button></a></body></html>
        '''
    
    # ログイン後：マイページ
    return '''
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{display:flex;flex-direction:column;align-items:center;padding:40px 20px;margin:0;font-family:sans-serif;background:#f0f4f8;}
    .card{background:white;padding:30px;border-radius:20px;box-shadow:0 4px 15px rgba(0,0,0,0.05);width:100%;max-width:400px;text-align:center;}
    button{width:100%;padding:18px;font-size:1.1rem;margin:10px 0;cursor:pointer;border:none;border-radius:12px;font-weight:bold;transition:0.2s;}
    .btn-main{background:#28a745;color:white;} .btn-sub{background:#6c757d;color:white;}</style></head>
    <body><div class="card"><h1>🏠 マイページ</h1><p>健康状態をチェックしましょう。</p>
    <a href="/measure"><button class="btn-main">📏 測定を開始する</button></a>
    <button class="btn-sub">📋 過去の履歴（準備中）</button></div></body></html>
    '''

# --- 測定画面 ---
@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('index'))
    return render_template('index.html')

# --- 保存完了画面 ---
@app.route('/success')
def success():
    return '''
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;text-align:center;}
    button{padding:15px 30px;font-size:1rem;background:#007bff;color:white;border:none;border-radius:10px;}</style></head>
    <body><h1>✅ 保存完了</h1><p>データをGoogle Driveに保存しました。</p><br>
    <a href="/"><button>マイページへ戻る</button></a></body></html>
    '''

@app.route('/login')
def login():
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
    session['credentials'] = {'token': creds.token, 'refresh_token': creds.refresh_token, 'token_uri': creds.token_uri, 'client_id': creds.client_id, 'client_secret': creds.client_secret, 'scopes': creds.scopes}
    return redirect(url_for('index'))

@app.route('/save', methods=['POST'])
def save():
    if 'credentials' not in session: return jsonify({"status": "error"}), 401
    try:
        data = request.json
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_body = "item,value\n" + "\n".join([f"{k},{v}" for k, v in data.items()])
        media = MediaInMemoryUpload(csv_body.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': filename}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)