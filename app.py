import json
import os
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

app = Flask(__name__)
# サーバー応答エラー(Port detected)を防ぐための設定
app.config['SERVER_NAME'] = None
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

# --- プロフィール暗号化/復号ロジック ---
def encrypt_data(data_dict):
    return base64.b64encode(json.dumps(data_dict).encode()).decode()

def decrypt_data(enc_str):
    try: return json.loads(base64.b64decode(enc_str.encode()).decode())
    except: return None

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
    session['credentials'] = {
        'token': creds.token, 'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri, 'client_id': creds.client_id,
        'client_secret': creds.client_secret, 'scopes': creds.scopes
    }
    # Google Driveからプロフィールを復元
    try:
        service = build('drive', 'v3', credentials=creds)
        files = service.files().list(q="name = 'profile_enc.dat' and trashed = false").execute().get('files', [])
        if files:
            content = service.files().get_media(fileId=files[0]['id']).execute().decode()
            u = decrypt_data(content)
            if u:
                session['user_info'] = u
                return redirect(url_for('mypage'))
    except: pass
    return redirect(url_for('profile_edit'))

@app.route('/profile_edit', methods=['GET', 'POST'])
def profile_edit():
    if 'credentials' not in session: return redirect(url_for('top'))
    if request.method == 'POST':
        u = {
            "name": request.form.get('name'),
            "gender": request.form.get('gender'),
            "birth": f"{request.form.get('birth_y')}-{request.form.get('birth_m').zfill(2)}-{request.form.get('birth_d').zfill(2)}",
            "zip": request.form.get('zip')
        }
        session['user_info'] = u
        try:
            creds = Credentials(**session['credentials'])
            service = build('drive', 'v3', credentials=creds)
            media = MediaInMemoryUpload(encrypt_data(u).encode(), mimetype='text/plain')
            files = service.files().list(q="name = 'profile_enc.dat' and trashed = false").execute().get('files', [])
            if files: service.files().update(fileId=files[0]['id'], media_body=media).execute()
            else: service.files().create(body={'name': 'profile_enc.dat'}, media_body=media).execute()
        except: pass
        return redirect(url_for('mypage'))

    u = session.get('user_info', {})
    b = u.get('birth', '1955-01-01').split('-')
    y_opts = "".join([f'<option value="{y}" {"selected" if str(y)==b[0] else ""}>{y}</option>' for y in range(1930, 2011)])
    m_opts = "".join([f'<option value="{m}" {"selected" if str(m).zfill(2)==b[1] else ""}>{m}</option>' for m in range(1, 13)])
    d_opts = "".join([f'<option value="{d}" {"selected" if str(d).zfill(2)==b[2] else ""}>{d}</option>' for d in range(1, 32)])

    return f'''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
    .card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto; text-align:left;}}
    input, select{{width:100%; padding:12px; margin:10px 0; border:1px solid #ccc; border-radius:8px; box-sizing:border-box; font-size:16px;}}
    .btn{{display:block; width:100%; padding:15px; background:#28a745; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer;}}
    </style></head><body><div class="card"><h2>プロフィール設定</h2>
    <form method="post">
        名前: <input type="text" name="name" value="{u.get('name','')}" required>
        性別: <select name="gender"><option value="1" {"selected" if u.get('gender')=='1' else ""}>男性</option><option value="2" {"selected" if u.get('gender')=='2' else ""}>女性</option></select>
        生年月日: <div style="display:flex; gap:5px;"><select name="birth_y">{y_opts}</select><select name="birth_m">{m_opts}</select><select name="birth_d">{d_opts}</select></div>
        郵便番号: <input type="text" name="zip" value="{u.get('zip','')}" placeholder="123-4567">
        <button type="submit" class="btn">保存してマイページへ</button>
    </form></div></body></html>'''

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info')
    if not u: return redirect(url_for('profile_edit'))
    return f'''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
    .card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto;}}
    .btn{{display:block; width:100%; padding:18px; margin:10px 0; border-radius:12px; font-weight:bold; text-decoration:none; box-sizing:border-box; font-size:1.1rem;}}
    .btn-main{{background:#28a745; color:white;}} 
    .btn-history{{background:#6c757d; color:white;}}
    </style></head><body><div class="card">
    <h2>マイページ</h2><p>こんにちは、{u.get('name')} さん</p>
    <a href="/measure" class="btn btn-main">測定を開始する</a>
    <a href="https://drive.google.com/" target="_blank" class="btn btn-history">過去の履歴を見る</a>
    <a href="/profile_edit" style="color:#007bff; text-decoration:none; font-size:0.9rem;">プロフィールを変更する</a>
    <a href="/logout" style="color:red; display:block; margin-top:20px;">ログアウト</a>
    </div></body></html>'''

@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info')
    if not u: return redirect(url_for('profile_edit'))
    return render_template('index.html', gender=u.get('gender', '1'))

@app.route('/save', methods=['POST'])
def save():
    try:
        data = request.json
        u = session.get('user_info', {})
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        q = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service.files().list(q=q).execute().get('files', [])
        f_id = folders[0]['id'] if folders else service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        headers = ["Date", "Name", "Gender", "Birth", "Zip"] + list(data.keys())
        values = [timestamp, u.get('name'), u.get('gender'), u.get('birth'), u.get('zip')] + list(data.values())
        
        csv_content = ",".join(headers) + "\n" + ",".join(map(str, values))
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': f"測定_{u.get('name')}_{datetime.now().strftime('%m%d_%H%M')}.csv", 'parents': [f_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/result', methods=['POST'])
def result():
    answers = json.loads(request.form.get('answers', '{}'))
    colors = json.loads(request.form.get('colors', '{}'))
    user = session.get('user_info', {})
    # レポート表示用に保存
    session['report_data'] = {
        'answers': answers, 
        'colors': colors, 
        'date': datetime.now().strftime('%Y/%m/%d %H:%M')
    }
    # result.htmlに判定結果とユーザー情報を渡す
    return render_template('result.html', answers=answers, colors=colors, user=user)

@app.route('/report')
def report():
    if 'credentials' not in session: return redirect(url_for('top'))
    data = session.get('report_data')
    user = session.get('user_info', {})
    if not data: return redirect(url_for('mypage'))
    # **dataで answers, colors, date を展開して渡す
    return render_template('report.html', **data, user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('top'))

if __name__ == '__main__':
    # Render等の本番環境用ポート設定
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)