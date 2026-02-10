import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

app = Flask(__name__)
app.secret_key = "frail_app_key_2024"

CLIENT_CONFIG = {
    "web": {
        "client_id": "734131799600-cn8qec6q6dqh24v93bf4ubabb0gtjm5d.apps.googleusercontent.com",
        "client_secret": "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",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["https://frail-system.onrender.com/callback"]
    }
}

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.appdata']

@app.route('/')
def top():
    if 'credentials' in session: return redirect(url_for('mypage'))
    return '''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;}
    button{padding:25px 50px;font-size:1.6rem;cursor:pointer;background:#007bff;color:white;border:none;border-radius:15px;box-shadow:0 5px 15px rgba(0,0,0,0.1);font-weight:bold;}</style></head>
    <body><h1 style="font-size:2.2rem;margin-bottom:50px;">フレイル測定アプリ</h1><a href="/login"><button>Googleでログイン</button></a></body></html>
    '''

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
    try:
        service = build('drive', 'v3', credentials=creds)
        q = "name = 'profile_data.json' and trashed = false"
        files = service.files().list(q=q, spaces='appDataFolder').execute().get('files', [])
        if files:
            content = service.files().get_media(fileId=files[0]['id']).execute()
            session['user_info'] = json.loads(content.decode('utf-8'))
            return redirect(url_for('mypage'))
    except Exception as e: print("Callback Profile Fetch Error:", e)
    return redirect(url_for('profile'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'credentials' not in session: return redirect(url_for('top'))
    if request.method == 'POST':
        birth = f"{request.form.get('birth_y')}-{request.form.get('birth_m')}-{request.form.get('birth_d')}"
        user_info = {"name": request.form.get('name'), "gender": request.form.get('gender'), "birth": birth, "zip": request.form.get('zip')}
        session['user_info'] = user_info
        try:
            creds = Credentials(**session['credentials'])
            service = build('drive', 'v3', credentials=creds)
            q = "name = 'profile_data.json' and trashed = false"
            files = service.files().list(q=q, spaces='appDataFolder').execute().get('files', [])
            content = json.dumps(user_info, ensure_ascii=False)
            media = MediaInMemoryUpload(content.encode('utf-8'), mimetype='application/json')
            if files: service.files().update(fileId=files[0]['id'], media_body=media).execute()
            else: service.files().create(body={'name': 'profile_data.json', 'parents': ['appDataFolder']}, media_body=media).execute()
        except Exception as e: print("Profile Save Error:", e)
        return redirect(url_for('mypage'))
    u = session.get('user_info', {})
    return render_template('profile.html', u=u) # profileは以前のセレクトボックス形式を想定

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    if 'user_info' not in session: return redirect(url_for('profile'))
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
    .card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto;}}
    .btn-start{{width:100%; padding:20px; background:#28a745; color:white; border:none; border-radius:15px; font-size:1.3rem; font-weight:bold; cursor:pointer; margin-top:10px;}}
    </style></head><body><div class="card">
    <h2>マイページ</h2><p>こんにちは、{session['user_info'].get('name')} さん</p>
    <a href="/consent"><button class="btn-start">測定を開始する</button></a>
    <br><a href="/logout" style="color:red; display:block; margin-top:20px;">ログアウト</a>
    </div></body></html>
    '''

@app.route('/consent')
def consent():
    return '''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body>
    <div style="padding:20px; text-align:center;"><h3>測定への同意</h3><p>データはGoogle Driveへ保存されます。</p>
    <a href="/measure"><button style="padding:15px 30px;">同意して開始</button></a></div></body></html>'''

@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('top'))
    return render_template('index.html', gender=session['user_info']['gender'])

@app.route('/save', methods=['POST'])
def save():
    if 'credentials' not in session: return jsonify({"status": "error"}), 401
    try:
        data = request.json
        u = session.get('user_info', {})
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        
        folder_id = None
        q_folder = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service.files().list(q=q_folder).execute().get('files', [])
        if folders: folder_id = folders[0]['id']
        else:
            folder = service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute()
            folder_id = folder.get('id')
        
        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        headers = ["時刻", "氏名", "性別", "生年月日", "郵便番号", "指輪っか", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "握力", "身長", "体重", "BMI"]
        values = [timestamp, u.get('name'), u.get('gender'), u.get('birth'), u.get('zip'), data.get('finger'), *[data.get(f'q{i}') for i in range(1, 16)], data.get('grip'), data.get('height'), data.get('weight'), data.get('bmi')]
        csv_content = ",".join(headers) + "\n" + ",".join(map(str, values))
        filename = f"測定_{u.get('name')}_{datetime.now().strftime('%m%d_%H%M')}.csv"
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/result', methods=['POST'])
def result():
    colors_json = request.form.get('colors')
    colors = json.loads(colors_json) if colors_json else {}
    return render_template('result.html', colors=colors)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('top'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))