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
    if 'credentials' in session: return redirect(url_for('profile'))
    return '<h1>フレイル測定</h1><a href="/login"><button style="padding:20px;font-size:20px;">Googleでログイン</button></a>'

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
    session['credentials'] = flow.credentials.__dict__
    return redirect(url_for('profile'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'credentials' not in session: return redirect(url_for('top'))
    if request.method == 'POST':
        session['user_info'] = {
            "name": request.form.get('name'),
            "gender": request.form.get('gender'),
            "birth": f"{request.form.get('y')}-{request.form.get('m')}-{request.form.get('d')}",
            "zip": request.form.get('zip')
        }
        return redirect(url_for('measure'))
    
    y_opts = "".join([f'<option value="{y}">{y}</option>' for y in range(1930, 2011)])
    return f'''
    <form method="POST" style="padding:20px;font-size:18px;">
        名前: <input type="text" name="name" required><br><br>
        性別: <select name="gender"><option value="1">男性</option><option value="2">女性</option></select><br><br>
        生年月日: <select name="y">{y_opts}</select>年 
        <select name="m">{"".join([f'<option value="{m}">{m}</option>' for m in range(1,13)])}</select>月 
        <select name="d">{"".join([f'<option value="{d}">{d}</option>' for d in range(1,32)])}</select>日<br><br>
        郵便番号: <input type="text" name="zip" required><br><br>
        <button type="submit" style="padding:10px 20px;">測定開始</button>
    </form>
    '''

@app.route('/measure')
def measure():
    if 'user_info' not in session: return redirect(url_for('profile'))
    return render_template('index.html', gender=session['user_info']['gender'])

@app.route('/save', methods=['POST'])
def save():
    try:
        data = request.json
        u = session.get('user_info', {})
        creds = Credentials(**session['credentials'])
        service = build('drive', 'v3', credentials=creds)
        
        # フォルダ確認・作成
        res = service.files().list(q="name='fraildata' and mimeType='application/vnd.google-apps.folder'").execute()
        f_id = res.get('files')[0]['id'] if res.get('files') else service.files().create(body={'name': 'fraildata', 'mimeType': 'application/vnd.google-apps.folder'}, fields='id').execute().get('id')

        csv_content = f"{u.get('name')},{u.get('gender')},{u.get('birth')},{data.get('bmi')}"
        media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
        service.files().create(body={'name': f"res_{u.get('name')}.csv", 'parents': [f_id]}, media_body=media).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))