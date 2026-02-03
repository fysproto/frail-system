import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'your-secret-key' # 本番はランダムな文字列に

# --- ダミーの認証・プロフィール判定ロジック ---
@app.route('/')
def top():
    return '<a href="/callback">ログイン（デモ）</a>'

@app.route('/callback')
def callback():
    session['credentials'] = True
    return redirect(url_for('mypage'))

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    if 'user_info' not in session: return redirect(url_for('profile'))
    return render_template('mypage.html', name=session['user_info'].get('name'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        session['user_info'] = {
            'name': request.form.get('name'),
            'birth': request.form.get('birth'),
            'gender': request.form.get('gender')
        }
        return redirect(url_for('mypage'))
    return '''
        <form method="post" style="padding:20px; font-family:sans-serif;">
            <h2>プロフィール登録</h2>
            名前: <input type="text" name="name" required><br><br>
            生年月日: <input type="date" name="birth" required><br><br>
            性別: <select name="gender"><option value="1">男性</option><option value="2">女性</option></select><br><br>
            <button type="submit">登録してマイページへ</button>
        </form>
    '''

@app.route('/consent')
def consent():
    return render_template('consent.html')

@app.route('/measure')
def measure():
    gender = session.get('user_info', {}).get('gender', '1')
    return render_template('index.html', gender=gender)

@app.route('/save', methods=['POST'])
def save():
    answers = request.json
    user = session.get('user_info', {})
    
    # ここでCSVデータを作成（プロフィール + 回答）
    csv_row = [user.get('name'), user.get('birth'), user.get('gender')] + list(answers.values())
    print("Saving to CSV:", csv_row) # サーバーログで確認用
    
    # 実際はここでGoogle Driveに保存する関数を呼ぶ
    return jsonify({"status": "success", "redirect": "/mypage"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))