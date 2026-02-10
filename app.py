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
    return '<html><body style="display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;font-family:sans-serif;background:#f0f4f8;"><h1>フレイル測定システム</h1><a href="/login"><button style="padding:20px 40px;font-size:1.5rem;background:#007bff;color:white;border:none;border-radius:10px;">Googleログイン</button></a></body></html>'

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
    session['credentials'] = flow.credentials.__dict__
    try:
        service = build('drive', 'v3', credentials=flow.credentials)
        files = service.files().list(q="name = 'profile_data.json'", spaces='appDataFolder').execute().get('files', [])
        if files:
            content = service.files().get_media(fileId=files[0]['id']).execute()
            session['user_info'] = json.loads(content.decode('utf-8'))
    except: pass
    return redirect(url_for('mypage'))

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info', {})
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{{padding:20px;font-family:sans-serif;background:#f0f4f8;text-align:center;}}
    .card{{background:white;padding:30px;border-radius:20px;box-shadow:0 4px 10px rgba(0,0,0,0.05);max-width:400px;margin:auto;}}
    .btn{{display:block;width:100%;padding:18px;margin:10px 0;border-radius:12px;font-weight:bold;font-size:1.1rem;text-decoration:none;text-align:center;box-sizing:border-box;}}
    .btn-main{{background:#28a745;color:white;}} .btn-sub{{background:#6c757d;color:white;}}
    </style></head><body><div class="card">
    <h2>マイページ</h2><p>{u.get('name', 'ゲスト')} 様</p>
    <a href="/measure" class="btn btn-main">測定を開始する</a>
    <a href="/history" class="btn btn-sub">過去の履歴を見る</a>
    <a href="/logout" style="color:red;display:block;margin-top:20px;">ログアウト</a>
    </div></body></html>'''

@app.route('/measure')
def measure():
    return render_template('index.html', gender=session.get('user_info', {}).get('gender', '1'))

@app.route('/save', methods=['POST'])
def save():
    data = request.json
    u = session.get('user_info', {})
    creds = Credentials(**session['credentials'])
    service = build('drive', 'v3', credentials=creds)
    
    q_f = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    folders = service.files().list(q=q_f).execute().get('files', [])
    f_id = folders[0]['id'] if folders else service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')
    
    now = datetime.now()
    headers = ["時刻", "氏名", "性別", "生年月日", "郵便番号", "指輪っか", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "握力", "身長", "体重", "BMI"]
    values = [now.strftime('%Y/%m/%d %H:%M'), u.get('name'), u.get('gender'), u.get('birth'), u.get('zip'), data.get('finger'), *[data.get(f'q{i}') for i in range(1, 16)], data.get('grip'), data.get('height'), data.get('weight'), data.get('bmi')]
    csv_line = ",".join(map(str, values))
    media = MediaInMemoryUpload((",".join(headers) + "\n" + csv_line).encode('utf-8-sig'), mimetype='text/csv')
    service.files().create(body={'name': f"測定_{u.get('name')}_{now.strftime('%m%d_%H%M')}.csv", 'parents': [f_id]}, media_body=media).execute()
    return jsonify({"status": "success"})

@app.route('/result', methods=['POST'])
def result():
    # フォームから回答データとおはじき色データを受け取る
    answers = json.loads(request.form.get('answers', '{}'))
    colors = json.loads(request.form.get('colors', '{}'))
    user = session.get('user_info', {})
    return render_template('result.html', answers=answers, colors=colors, user=user, date=datetime.now().strftime('%Y/%m/%d'))

@app.route('/history')
def history():
    creds = Credentials(**session['credentials'])
    service = build('drive', 'v3', credentials=creds)
    q = "name contains '測定_' and mimeType = 'text/csv' and trashed = false"
    files = service.files().list(q=q, orderBy="createdTime desc", pageSize=15).execute().get('files', [])
    return render_template('history.html', files=files)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('top'))

if __name__ == '__main__':
    app.run(debug=True)