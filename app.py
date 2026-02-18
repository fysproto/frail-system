import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

app = Flask(__name__)
app.secret_key = "frail_app_key_2026_final"

# Google OAuth 設定
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

@app.route('/')
def top():
    if 'credentials' in session: return redirect(url_for('mypage'))
    return '''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;}
    button{padding:25px 50px;font-size:1.6rem;cursor:pointer;background:#007bff;color:white;border:none;border-radius:15px;font-weight:bold;}</style></head>
    <body><h1 style="margin-bottom:50px;">フレイル測定アプリ</h1><a href="/login"><button>Googleでログイン</button></a></body></html>'''

@app.route('/login')
def login():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = url_for('callback', _external=True)
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/callback')
def callback():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = url_for('callback', _external=True)
    flow.fetch_token(code=request.args.get('code'))
    creds = flow.credentials
    session['credentials'] = {'token': creds.token, 'refresh_token': creds.refresh_token, 'token_uri': creds.token_uri, 'client_id': creds.client_id, 'client_secret': creds.client_secret, 'scopes': creds.scopes}
    session['user_info'] = {"name": "利用者様", "gender": "1"} 
    return redirect(url_for('mypage'))

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info', {})
    # 履歴ボタンを追加したマイページ
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
    .card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto;}}
    .btn{{display:block; width:100%; padding:18px; margin:10px 0; border-radius:12px; font-weight:bold; text-decoration:none; box-sizing:border-box; font-size:1.1rem;}}
    .btn-main{{background:#28a745; color:white;}} 
    .btn-history{{background:#6c757d; color:white;}}
    </style></head><body><div class="card">
    <h2>マイページ</h2><p>こんにちは、{u.get('name')} さん</p>
    <a href="/measure" class="btn btn-main">測定を開始する</a>
    <a href="https://drive.google.com/" target="_blank" class="btn btn-history">過去の履歴を見る</a>
    <a href="/logout" style="color:red; display:block; margin-top:20px;">ログアウト</a>
    </div></body></html>'''

@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('top'))
    return render_template('index.html', gender=session['user_info'].get('gender', '1'))

@app.route('/save', methods=['POST'])
def save():
    try:
        data = request.json
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        # フォルダ作成・CSV保存ロジック（既存維持）
        q = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service.files().list(q=q).execute().get('files', [])
        f_id = folders[0]['id'] if folders else service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')
        csv_content = f"Date,{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        for k, v in data.items(): csv_content += f"{k},{v}\n"
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': f"測定_{datetime.now().strftime('%m%d_%H%M')}.csv", 'parents': [f_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/result', methods=['POST'])
def result():
    # index.htmlから送られた回答テキストと色を受け取る
    answers = json.loads(request.form.get('answers', '{}'))
    colors = json.loads(request.form.get('colors', '{}'))
    user = session.get('user_info', {})
    return render_template('result.html', answers=answers, colors=colors, user=user, date=datetime.now().strftime('%Y/%m/%d'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('top'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))