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
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- セキュリティ：暗号化ロジック ---
def encrypt_data(data_dict):
    return base64.b64encode(json.dumps(data_dict).encode()).decode()

def decrypt_data(enc_str):
    try:
        return json.loads(base64.b64decode(enc_str.encode()).decode())
    except:
        return None

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
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    try:
        service = build('drive', 'v3', credentials=creds)
        files = service.files().list(q="name = 'profile_enc.dat' and trashed = false").execute().get('files', [])
        if files:
            content = service.files().get_media(fileId=files[0]['id']).execute().decode()
            u = decrypt_data(content)
            if u:
                session['user_info'] = u
                return redirect(url_for('mypage'))
    except:
        pass
    
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
            if files:
                service.files().update(fileId=files[0]['id'], media_body=media).execute()
            else:
                service.files().create(body={'name': 'profile_enc.dat'}, media_body=media).execute()
        except:
            pass
        return redirect(url_for('mypage'))

    u = session.get('user_info', {})
    b = u.get('birth', '1955-01-01').split('-')
    y_opts = "".join([f'<option value="{y}" {"selected" if str(y)==b[0] else ""}>{y}</option>' for y in range(1920, 2027)])
    m_opts = "".join([f'<option value="{m}" {"selected" if str(m).zfill(2)==b[1] else ""}>{m}</option>' for m in range(1, 13)])
    d_opts = "".join([f'<option value="{d}" {"selected" if str(d).zfill(2)==b[2] else ""}>{d}</option>' for d in range(1, 32)])

    return f'''
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}
        .card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto; text-align:left;}}
        input, select{{width:100%; padding:12px; margin:10px 0; border:1px solid #ccc; border-radius:8px; box-sizing:border-box; font-size:16px;}}
        .btn{{display:block; width:100%; padding:15px; background:#28a745; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer; box-sizing:border-box;}}
        .btn:disabled{{background:#6c757d; cursor:not-allowed;}}
    </style>
    <script>
        function saveProfile(btn){{
            btn.disabled = true;
            btn.innerText = "保存中...";
            btn.form.submit();
        }}
    </script>
    </head><body><div class="card">
    <h2>プロフィール設定</h2>
    <form method="post">
        名前: <input type="text" name="name" value="{u.get('name','')}" required placeholder="お名前">
        性別: <select name="gender">
            <option value="1" {"selected" if u.get('gender')=='1' else ""}>男性</option>
            <option value="2" {"selected" if u.get('gender')=='2' else ""}>女性</option>
        </select>
        生年月日: <div style="display:flex; gap:5px;"><select name="birth_y">{y_opts}</select><select name="birth_m">{m_opts}</select><select name="birth_d">{d_opts}</select></div>
        郵便番号: <input type="text" name="zip" value="{u.get('zip','')}" placeholder="123-4567">
        <button type="button" class="btn" onclick="saveProfile(this)">保存してマイページへ</button>
    </form></div></body></html>'''

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info', {"name": "利用者様"})
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
    <a href="/profile_edit" style="color:#007bff; text-decoration:none; font-size:0.9rem; display:block; margin-top:10px;">プロフィールを変更する</a>
    <a href="/logout" style="color:red; display:block; margin-top:20px;">ログアウト</a>
    </div></body></html>'''

@app.route('/measure')
def measure():
    if 'credentials' not in session: return redirect(url_for('top'))
    return '''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>
    body{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}
    .card{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:500px; margin:auto; text-align:left; box-sizing:border-box;}
    .box{height:150px; overflow-y:scroll; border:1px solid #eee; padding:10px; margin:15px 0; font-size:0.85rem; color:#666;}
    .btn-start{display:block; width:100%; padding:18px; background:#28a745; color:white; text-align:center; text-decoration:none; border-radius:12px; font-weight:bold; box-sizing:border-box;}
    </style></head><body><div class="card"><h2>測定前の同意</h2>
    <p>測定結果はご自身のGoogleドライブに保存されます。内容を確認し同意して開始してください。</p>
    <div class="box">【同意事項】<br>・収集したデータはフレイル判定のみに使用します。<br>・結果は個人の参考用です。<br>・データはご自身のGoogleドライブ「fraildata」フォルダに保存されます。</div>
    <a href="/start_test" class="btn-start">同意して測定を開始する</a>
    <p style="text-align:center;"><a href="/mypage" style="color:#666; font-size:0.8rem;">マイページへ戻る</a></p>
    </div></body></html>'''

@app.route('/start_test')
def start_test():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info', {})
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
        
        csv_content = f"Date,{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        csv_content += f"Name,{u.get('name')}\nGender,{u.get('gender')}\nBirth,{u.get('birth')}\nZip,{u.get('zip')}\n"
        for k, v in data.items(): csv_content += f"{k},{v}\n"
        
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': f"測定_{u.get('name')}_{datetime.now().strftime('%m%d_%H%M')}.csv", 'parents': [f_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/result', methods=['POST'])
def result():
    answers = json.loads(request.form.get('answers', '{}'))
    colors = json.loads(request.form.get('colors', '{}'))
    user = session.get('user_info', {})
    session['report_data'] = {'answers': answers, 'colors': colors, 'date': datetime.now().strftime('%Y/%m/%d %H:%M')}
    return render_template('result.html', answers=answers, colors=colors, user=user)

@app.route('/report')
def report():
    if 'credentials' not in session: return redirect(url_for('top'))
    data = session.get('report_data')
    user = session.get('user_info', {})
    if not data: return redirect(url_for('mypage'))
    return render_template('report.html', **data, user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('top'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
# --- 過去履歴機能の追加ルーチン ---

@app.route('/history_list')
def history_list():
    if 'credentials' not in session: return redirect(url_for('top'))
    # ここは一覧ページのHTMLを返すだけ。実際のデータはJSで取得するわ。
    return render_template('history.html')

@app.route('/api/get_history')
def api_get_history():
    if 'credentials' not in session: return jsonify([])
    page = int(request.args.get('page', 0))
    creds = Credentials(**session['credentials'])
    service = build('drive', 'v3', credentials=creds)
    
    # fraildataフォルダを探す
    q_folder = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    folders = service.files().list(q=q_folder).execute().get('files', [])
    if not folders: return jsonify([])
    
    # フォルダ内のCSVを日付順に取得
    q_files = f"'{folders[0]['id']}' in parents and mimeType = 'text/csv' and trashed = false"
    # 10件ずつ取得（pageSizeで制御）
    results = service.files().list(
        q=q_files, 
        orderBy="createdTime desc", 
        pageSize=10,
        fields="nextPageToken, files(id, name, createdTime)"
    ).execute()
    
    files = results.get('files', [])
    # 高齢者・お医者さん向けに日付をフォーマット
    history_data = []
    for f in files:
        dt = datetime.fromisoformat(f['createdTime'].replace('Z', '+00:00'))
        history_data.append({
            "id": f['id'],
            "name": f['name'],
            "display_date": dt.strftime('%Y年 %m月 %d日 (%a)')
        })
    return jsonify(history_data)

@app.route('/history_view')
def history_view():
    if 'credentials' not in session: return redirect(url_for('top'))
    target_id = request.args.get('id')
    compare_id = request.args.get('compare_id') # 無ければ「前回」を自動取得するロジックを後で追加
    
    # ここでCSVを読み込み、新旧比較して「網掛けクラス」を決定する
    # ※詳細は history_report.html 作成時に作り込むわね
    return render_template('history_report.html', target_id=target_id, compare_id=compare_id)