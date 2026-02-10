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
SCOPES = ['https://www.googleapis.com/auth/drive.file']

@app.route('/')
def top():
    if 'credentials' in session:
        return redirect(url_for('mypage'))
    return '''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;}
    button{padding:25px 50px;font-size:1.6rem;cursor:pointer;background:#007bff;color:white;border:none;border-radius:15px;box-shadow:0 5px 15px rgba(0,0,0,0.1);font-weight:bold;}</style></head>
    <body><h1 style="font-size:2.2rem;margin-bottom:50px;">フレイル測定アプリ</h1><a href="/login"><button>Googleでログイン</button></a></body></html>
    '''

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    if 'user_info' not in session: return redirect(url_for('profile'))
    u = session['user_info']
    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
    .card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto;}}
    .btn-start{{width:100%; padding:20px; background:#28a745; color:white; border:none; border-radius:15px; font-size:1.3rem; font-weight:bold; cursor:pointer; margin-top:10px;}}
    .btn-history{{width:100%; padding:20px; background:#6c757d; color:white; border:none; border-radius:15px; font-size:1.1rem; font-weight:bold; cursor:pointer; margin-top:20px;}}
    </style></head><body><div class="card">
    <h2>マイページ</h2>
    <a href="/consent"><button class="btn-start">測定を開始する</button></a>
    <button class="btn-history" onclick="alert('履歴機能は準備中です')">過去の履歴を見る</button>
    </div></body></html>
    '''

@app.route('/consent')
def consent():
    if 'credentials' not in session: return redirect(url_for('top'))
    return '''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
    .box{{background:white; padding:20px; border-radius:15px; text-align:left; height:300px; overflow-y:auto; border:1px solid #ddd;}}
    button{{width:100%; padding:20px; background:#007bff; color:white; border:none; border-radius:15px; font-size:1.2rem; margin-top:20px;}}
    </style></head><body><div style="max-width:400px; margin:auto;"><h3>測定への同意</h3>
    <div class="box"><p>【同意事項】</p><p>・測定データは統計的に処理され、個人の特定はされません。</p><p>・データはGoogle Driveへ保存されます。</p></div>
    <a href="/measure"><button>同意して開始する</button></a></div></body></html>
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
        return redirect(url_for('mypage'))

    y_opts = "".join([f'<option value="{y}" {"selected" if y==1955 else ""}>{y}</option>' for y in range(1930, 2011)])
    m_opts = "".join([f'<option value="{m}">{m}</option>' for m in range(1, 13)])
    d_opts = "".join([f'<option value="{d}">{d}</option>' for d in range(1, 32)])

    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <style>body{{padding:15px; font-family:sans-serif; background:#f0f4f8; margin:0;}}
    .card{{background:white; padding:20px; border-radius:15px; width:100%; max-width:400px; margin:auto; box-shadow:0 4px 10px rgba(0,0,0,0.05);}}
    input, select{{width:100%; padding:12px; margin:10px 0; border:1px solid #ddd; border-radius:8px; font-size:16px;}}
    .date-group{{display:flex; gap:5px; align-items:center;}}
    button{{width:100%; padding:15px; background:#28a745; color:white; border:none; border-radius:8px; font-size:1.1rem; font-weight:bold;}}</style></head>
    <body><div class="card"><h2>📋 基本情報の入力</h2><form method="POST">
    <label>お名前</label><input type="text" name="name" required>
    <label>性別</label><select name="gender" required><option value="">選択</option><option value="1">男性</option><option value="2">女性</option></select>
    <label>生年月日</label><div class="date-group"><select name="birth_y">{y_opts}</select>年<select name="birth_m">{m_opts}</select>月<select name="birth_d">{d_opts}</select>日</div>
    <label>郵便番号</label><input type="text" name="zip" required><button type="submit">次へ進む</button></form></div></body></html>
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
        
     # 1. 'fraildata' という名前のフォルダがあるか検索
        folder_id = None
        q_folder = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service.files().list(q=q_folder).execute().get('files', [])
        
        if folders:
            # フォルダが見つかったらそのIDを使う
            folder_id = folders[0]['id']
        else:
            # 見つからなければ新規作成
            folder_metadata = {
                'name': 'fraildata',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
        
        # 2. 保存データの作成
        timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        headers = ["時刻", "氏名", "性別", "生年月日", "郵便番号", "指輪っか", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15", "握力", "身長", "体重", "BMI"]
        values = [timestamp, u.get('name'), u.get('gender'), u.get('birth'), u.get('zip'), data.get('finger'), *[data.get(f'q{i}') for i in range(1, 16)], data.get('grip'), data.get('height'), data.get('weight'), data.get('bmi')]
        
        csv_content = ",".join(headers) + "\n" + ",".join(map(str, values))
        filename = f"測定_{u.get('name')}_{datetime.now().strftime('%m%d_%H%M')}.csv"
        
        # 3. 指定したフォルダID（parents）の中にファイルを保存
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(
            body={
                'name': filename,
                'parents': [folder_id]  
            },
            media_body=media
        ).execute()
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)