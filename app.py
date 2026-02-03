import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

app = Flask(__name__)
app.secret_key = "frail_app_key_secret" # 本番ではランダムな文字列を推奨

# --- 設定 (RenderのURLに合わせて) ---
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

# --- [1] TOPページ ---
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

# --- [2] プロフィール・同意入力画面 ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'credentials' not in session: return redirect(url_for('top'))
    
    if request.method == 'POST':
        # 入力データをセッションに保存
        session['user_info'] = {
            "name": request.form.get('name'),
            "gender": request.form.get('gender'), # "1":男, "2":女
            "birth": request.form.get('birth'),
            "zip": request.form.get('zip')
        }
        return redirect(url_for('measure'))

    return '''
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{padding:20px;font-family:sans-serif;background:#f0f4f8;}
    .card{background:white;padding:25px;border-radius:15px;max-width:400px;margin:auto;box-shadow:0 4px 10px rgba(0,0,0,0.05);}
    input, select{width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:8px;box-sizing:border-box;}
    button{width:100%;padding:15px;background:#28a745;color:white;border:none;border-radius:8px;font-size:1.1rem;font-weight:bold;cursor:pointer;}
    .consent{font-size:0.85rem;color:#666;margin:15px 0;border-top:1px solid #eee;padding-top:15px;}</style></head>
    <body><div class="card"><h2>📋 基本情報の入力</h2>
    <form method="POST">
        <input type="text" name="name" placeholder="お名前" required>
        <select name="gender" required><option value="">性別を選択</option><option value="1">男性</option><option value="2">女性</option></select>
        <input type="date" name="birth" required>
        <input type="text" name="zip" placeholder="郵便番号 (例: 123-4567)" required>
        <div class="consent">
            <input type="checkbox" required> 自治体および運営へのデータ提供に同意します
        </div>
        <button type="submit">測定を開始する</button>
    </form></div></body></html>
    '''

# --- [3] 測定画面 ---
@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('top'))
    if 'user_info' not in session: return redirect(url_for('profile'))
    # 性別データをテンプレートに渡す
    return render_template('index.html', gender=session['user_info']['gender'])

# --- [4] 保存完了画面 ---
@app.route('/success')
def success():
    return redirect(url_for('top')) # または元の完了画面

# --- 認証ロジック ---
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
    session['credentials'] = {
        'token': creds.token, 'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri, 'client_id': creds.client_id,
        'client_secret': creds.client_secret, 'scopes': creds.scopes
    }
    return redirect(url_for('profile'))

# --- データ保存API ---
@app.route('/save', methods=['POST'])
def save():
    if 'credentials' not in session: return jsonify({"status": "error"}), 401
    try:
        data = request.json
        u = session.get('user_info', {})
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)

        # フォルダ「fraildata」を取得または作成
        folder_id = None
        q = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service.files().list(q=q).execute().get('files', [])
        if folders: folder_id = folders[0]['id']
        else:
            folder_id = service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')

        # 横1行のCSVデータ作成
        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        headers = ["時刻", "氏名", "性別", "生年月日", "郵便番号", "指輪っか", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "握力", "身長", "体重", "BMI"]
        values = [
            timestamp, u.get('name'), u.get('gender'), u.get('birth'), u.get('zip'),
            data.get('finger'), *[data.get(f'q{i}') for i in range(1, 16)],
            data.get('grip'), data.get('height'), data.get('weight'), data.get('bmi')
        ]
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