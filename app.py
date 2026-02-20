import json
import os
import base64
import csv
import io
from datetime import datetime, timedelta, timezone
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

def encrypt_data(data_dict):
    return base64.b64encode(json.dumps(data_dict).encode()).decode()

def decrypt_data(enc_str):
    try: return json.loads(base64.b64decode(enc_str.encode()).decode())
    except: return None

def judge_colors(answers, gender):
    c = {}
    f = answers.get('finger')
    c['finger'] = 'red' if f == '隙間ができる' else 'blue'
    try:
        bmi = float(answers.get('bmi', 0))
        c['bmi'] = 'red' if bmi < 21.5 else 'blue'
    except: c['bmi'] = 'gray'
    try:
        g = float(answers.get('grip', 0))
        threshold = 28.0 if gender == '1' else 18.0
        c['grip'] = 'red' if g < threshold else 'blue'
    except: c['grip'] = 'gray'
    
    red_defs = {
        "q1": ["あまりよくない", "よくない"], "q2": ["やや不満", "不満"],
        "q3": ["いいえ"], "q4": ["はい"], "q5": ["はい"], "q6": ["はい"],
        "q7": ["はい"], "q8": ["はい"], "q9": ["いいえ"], "q10": ["はい"],
        "q11": ["はい"], "q12": ["吸っている"], "q13": ["いいえ"],
        "q14": ["いいえ"], "q15": ["いいえ"]
    }
    for qid, red_list in red_defs.items():
        val = answers.get(qid)
        is_bad = val in red_list
        if qid in ["q1", "q2", "q12"]:
            c[qid] = 'yellow' if is_bad else 'white'
        else:
            c[qid] = 'red' if is_bad else 'blue'
    return c

@app.route('/')
def top():
    if 'credentials' in session: return redirect(url_for('mypage'))
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;background:#f0f4f8;}button{padding:25px 50px;font-size:1.6rem;cursor:pointer;background:#007bff;color:white;border:none;border-radius:15px;font-weight:bold;}</style></head><body><h1 style="margin-bottom:50px;">フレイル測定アプリ</h1><a href="/login"><button>Googleでログイン</button></a></body></html>'

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
        files = service.files().list(q="name = 'profile_enc.dat' and trashed = false").execute().get('files', [])
        if files:
            content = service.files().get_media(fileId=files[0]['id']).execute().decode()
            u = decrypt_data(content)
            if u: session['user_info'] = u
    except: pass
    return redirect(url_for('mypage'))

@app.route('/profile_edit', methods=['GET', 'POST'])
def profile_edit():
    if 'credentials' not in session: return redirect(url_for('top'))
    if request.method == 'POST':
        u = {"name": request.form.get('name'), "gender": request.form.get('gender'), 
             "birth": f"{request.form.get('birth_y')}-{request.form.get('birth_m').zfill(2)}-{request.form.get('birth_d').zfill(2)}",
             "zip": request.form.get('zip')}
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
    y_opts = "".join([f'<option value="{y}" {"selected" if str(y)==b[0] else ""}>{y}</option>' for y in range(1920, 2027)])
    m_opts = "".join([f'<option value="{m}" {"selected" if str(m).zfill(2)==b[1] else ""}>{m}</option>' for m in range(1, 13)])
    d_opts = "".join([f'<option value="{d}" {"selected" if str(d).zfill(2)==b[2] else ""}>{d}</option>' for d in range(1, 32)])
    return f'''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}.card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto; text-align:left;}}input, select{{width:100%; padding:12px; margin:10px 0; border:1px solid #ccc; border-radius:8px; box-sizing:border-box; font-size:16px;}}.btn{{display:block; width:100%; padding:15px; background:#28a745; color:white; border:none; border-radius:12px; font-weight:bold; cursor:pointer; box-sizing:border-box;}}</style>
    <script>function saveProfile(btn){{btn.disabled=true; btn.innerText="保存中..."; btn.form.submit();}}</script>
    </head><body><div class="card"><h2>プロフィール設定</h2><form method="post">名前: <input type="text" name="name" value="{u.get('name','')}" required>性別: <select name="gender"><option value="1" {"selected" if u.get('gender')=='1' else ""}>男性</option><option value="2" {"selected" if u.get('gender')=='2' else ""}>女性</option></select>生年月日: <div style="display:flex; gap:5px;"><select name="birth_y">{y_opts}</select><select name="birth_m">{m_opts}</select><select name="birth_d">{d_opts}</select></div>郵便番号: <input type="text" name="zip" value="{u.get('zip','')}" placeholder="123-4567"><button type="button" class="btn" onclick="saveProfile(this)">保存してマイページへ</button></form></div></body></html>'''

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    u = session.get('user_info', {"name": "利用者様"})
    return f'''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}}.card{{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:400px; margin:auto;}}.btn{{display:block; width:100%; padding:18px; margin:10px 0; border-radius:12px; font-weight:bold; text-decoration:none; box-sizing:border-box; font-size:1.1rem;}}.btn-main{{background:#28a745; color:white;}}.btn-history{{background:#6c757d; color:white;}}</style></head>
    <body><div class="card"><h2>マイページ</h2><p>こんにちは、{u.get('name')} さん</p><a href="/measure" class="btn btn-main">測定を開始する</a><a href="/history_list" class="btn btn-history">過去の履歴を見る</a><a href="/profile_edit" style="color:#007bff; text-decoration:none; font-size:0.9rem; display:block; margin-top:10px;">プロフィールを変更する</a><a href="/logout" style="color:red; display:block; margin-top:20px;">ログアウト</a></div></body></html>'''

@app.route('/measure')
def measure():
    return '''<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{padding:20px; font-family:sans-serif; background:#f0f4f8; text-align:center;}.card{background:white; padding:30px; border-radius:20px; box-shadow:0 4px 10px rgba(0,0,0,0.05); max-width:500px; margin:auto; text-align:left; box-sizing:border-box;}.box{height:150px; overflow-y:scroll; border:1px solid #eee; padding:10px; margin:15px 0; font-size:0.85rem; color:#666;}.btn-start{display:block; width:100%; padding:18px; background:#28a745; color:white; text-align:center; text-decoration:none; border-radius:12px; font-weight:bold; box-sizing:border-box;}</style>
    </head><body><div class="card"><h2>測定前の同意</h2><p>測定結果はご自身のGoogleドライブに保存されます。内容を確認し同意して開始してください。</p><div class="box">【同意事項】<br>・収集したデータはフレイル判定のみに使用します。<br>・結果は個人の参考用です。<br>・データはご自身のGoogleドライブ「fraildata」フォルダに保存されます。</div><a href="/start_test" class="btn-start">同意して測定を開始する</a><p style="text-align:center;"><a href="/mypage" style="color:#666; font-size:0.8rem;">マイページへ戻る</a></p></div></body></html>'''

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
        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)
        q = "name = 'fraildata' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        folders = service.files().list(q=q).execute().get('files', [])
        f_id = folders[0]['id'] if folders else service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')
        csv_content = f"Date,{now_jst.strftime('%Y-%m-%d %H:%M')}\nName,{u.get('name')}\nGender,{u.get('gender')}\nBirth,{u.get('birth')}\nZip,{u.get('zip')}\n"
        for k, v in data.items(): csv_content += f"{k},{v}\n"
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': f"測定_{u.get('name')}_{now_jst.strftime('%m%d_%H%M')}.csv", 'parents': [f_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/result', methods=['POST'])
def result():
    answers = json.loads(request.form.get('answers', '{}'))
    user = session.get('user_info', {})
    colors = judge_colors(answers, user.get('gender', '1'))
    jst = timezone(timedelta(hours=9))
    session['report_data'] = {'answers': answers, 'colors': colors, 'date': datetime.now(jst).strftime('%Y/%m/%d %H:%M')}
    return render_template('result.html', answers=answers, colors=colors, user=user)

@app.route('/report')
def report():
    if 'credentials' not in session: return redirect(url_for('top'))
    data = session.get('report_data')
    if not data: return redirect(url_for('mypage'))
    user = session.get('user_info', {})
    return render_template('report.html', **data, user=user, prev_colors=None)

@app.route('/history_list')
def history_list():
    if 'credentials' not in session: return redirect(url_for('top'))
    return render_template('history.html')

@app.route('/api/get_history')
def api_get_history():
    if 'credentials' not in session: return jsonify([])
    try:
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        q_f = "name = 'fraildata' and trashed = false"
        folders = service.files().list(q=q_f).execute().get('files', [])
        if not folders: return jsonify([])
        q_csv = f"'{folders[0]['id']}' in parents and mimeType = 'text/csv' and trashed = false"
        results = service.files().list(q=q_csv, orderBy="createdTime desc", pageSize=20, fields="files(id, name, createdTime)").execute()
        history_data = []
        days_map = ["月", "火", "水", "木", "金", "土", "日"]
        jst = timezone(timedelta(hours=9))
        for f in results.get('files', []):
            dt = datetime.fromisoformat(f['createdTime'].replace('Z', '+00:00')).astimezone(jst)
            display_date = dt.strftime(f'%Y年%m月%d日({days_map[dt.weekday()]}) %H:%M')
            history_data.append({"id": f['id'], "display_date": display_date})
        return jsonify(history_data)
    except: return jsonify([])

@app.route('/history_view')
def history_view():
    if 'credentials' not in session: return redirect(url_for('top'))
    tid = request.args.get('id')
    try:
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        def parse_csv(fid):
            content = service.files().get_media(fileId=fid).execute().decode('utf-8-sig')
            r = csv.reader(io.StringIO(content))
            d = {"answers": {}}
            gv = "1"
            for row in r:
                if len(row) < 2: continue
                if row[0] == "Date": d["date"] = row[1]
                elif row[0] == "Gender": gv = row[1]
                elif row[0] not in ["Name", "Birth", "Zip"]: d["answers"][row[0]] = row[1]
            d["colors"] = judge_colors(d["answers"], gv)
            return d
        curr = parse_csv(tid)
        q_f = "name = 'fraildata' and trashed = false"
        folders = service.files().list(q=q_f).execute().get('files', [])
        pc = None
        if folders:
            q_csv = f"'{folders[0]['id']}' in parents and mimeType = 'text/csv' and trashed = false"
            res = service.files().list(q=q_csv, orderBy="createdTime desc", fields="files(id)").execute()
            files = res.get('files', [])
            for i, f in enumerate(files):
                if f['id'] == tid and i + 1 < len(files):
                    pc = parse_csv(files[i+1]['id'])['colors']
                    break
        user = session.get('user_info', {})
        return render_template('report.html', **curr, user=user, prev_colors=pc)
    except: return redirect(url_for('history_list'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('top'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))