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

# --- Google OAuth 設定 ---
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
    if 'credentials' in session:
        return redirect(url_for('profile'))
    return '''
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;}
    button{padding:25px 50px;font-size:1.6rem;cursor:pointer;background:#007bff;color:white;border:none;border-radius:15px;box-shadow:0 5px 15px rgba(0,0,0,0.1);font-weight:bold;}</style></head>
    <body><h1 style="font-size:2.2rem;margin-bottom:50px;">フレイル測定アプリ</h1><a href="/login"><button>Googleでログイン</button></a></body></html>
    '''

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'credentials' not in session: return redirect(url_for('top'))
    if request.method == 'POST':
        birth = f"{request.form.get('birth_y')}-{request.form.get('birth_m')}-{request.form.get('birth_d')}"
        session['user_info'] = {
            "name": request.form.get('name'),
            "gender": request.form.get('gender'),
            "birth": birth,
            "zip": request.form.get('zip')
        }
        return redirect(url_for('measure'))

    # セレクトボックスの選択肢生成
    y_opts = "".join([f'<option value="{y}" {"selected" if y==1955 else ""}>{y}</option>' for y in range(1930, 2011)])
    m_opts = "".join([f'<option value="{m}">{m}</option>' for m in range(1, 13)])
    d_opts = "".join([f'<option value="{d}">{d}</option>' for d in range(1, 32)])

    return f'''
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <style>
        body{{padding:15px; font-family:sans-serif; background:#f0f4f8; margin:0; box-sizing:border-box; overflow-x:hidden;}}
        .card{{background:white; padding:20px; border-radius:15px; width:100%; max-width:400px; margin:auto; box-shadow:0 4px 10px rgba(0,0,0,0.05); box-sizing:border-box;}}
        input, select{{width:100%; padding:12px; margin:10px 0; border:1px solid #ddd; border-radius:8px; box-sizing:border-box; font-size:16px; background:white;}}
        .date-group{{display:flex; gap:5px; align-items:center; margin:10px 0;}}
        .date-group select{{flex:1; margin:0;}}
        button{{width:100%; padding:15px; background:#28a745; color:white; border:none; border-radius:8px; font-size:1.1rem; font-weight:bold; cursor:pointer; margin-top:20px;}}
    </style></head>
    <body><div class="card"><h2>📋 基本情報の入力</h2>
    <form method="POST">
        <label style="font-size:0.8rem; color:#666;">お名前</label><input type="text" name="name" required>
        <label style="font-size:0.8rem; color:#666;">性別</label>
        <select name="gender" required><option value="">選択してください</option><option value="1">男性</option><option value="2">女性</option></select>
        <label style="font-size:0.8rem; color:#666;">生年月日</label>
        <div class="date-group"><select name="birth_y">{y_opts}</select>年<select name="birth_m">{m_opts}</select>月<select name="birth_d">{d_opts}</select>日</div>
        <label style="font-size:0.8rem; color:#666;">郵便番号</label><input type="text" name="zip" placeholder="123-4567" required>
        <button type="submit">測定を開始する</button>
    </form></div></body></html>
    '''

@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('top'))
    if 'user_info' not in session: return redirect(url_for('profile'))
    return render_template('index.html', gender=session['user_info']['gender'])

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
    return redirect(url_for('profile'))

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
        else: folder_id = service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')
        
        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        headers = ["時刻", "氏名", "性別", "生年月日", "郵便番号", "指輪っか", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "握力", "身長", "体重", "BMI"]
        values = [timestamp, u.get('name'), u.get('gender'), u.get('birth'), u.get('zip'), data.get('finger'), *[data.get(f'q{i}') for i in range(1, 16)], data.get('grip'), data.get('height'), data.get('weight'), data.get('bmi')]
        
        csv_row = ",".join(headers) + "\n" + ",".join(map(str, values))
        filename = f"測定_{u.get('name')}_{datetime.now().strftime('%m%d_%H%M')}.csv"
        media = MediaInMemoryUpload(csv_row.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)