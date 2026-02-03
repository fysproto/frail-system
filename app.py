import os
from flask import Flask, render_template, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# --- 以前のGoogle API認証・Drive保存関数をここに残しておく ---
# def save_to_google_drive(row): ... 

@app.route('/')
def top():
    # ログインしていればマイページ、していなければログイン画面
    if 'credentials' in session:
        return redirect(url_for('mypage'))
    return '<div style="text-align:center; padding:50px;"><a href="/callback" style="font-size:1.5rem;">Googleでログイン</a></div>'

@app.route('/callback')
def callback():
    # ここでGoogle認証を行う（以前のロジック）
    session['credentials'] = True 
    return redirect(url_for('mypage'))

@app.route('/mypage')
def mypage():
    if 'credentials' not in session: return redirect(url_for('top'))
    # 初回のみプロフィールへ、2回目以降はマイページ
    if 'user_info' not in session:
        return redirect(url_for('profile'))
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
    # プロフィール入力フォーム
    return render_template('profile.html')

@app.route('/consent')
def consent():
    return render_template('consent.html')

@app.route('/measure')
def measure():
    if 'user_info' not in session: return redirect(url_for('profile'))
    gender = session['user_info'].get('gender', '1')
    return render_template('index.html', gender=gender)

@app.route('/save', methods=['POST'])
def save():
    if 'user_info' not in session: return jsonify({"status":"error"}), 401
    
    answers = request.json
    user = session['user_info']
    
    # プロフィール情報と回答を合体させたCSV行を作成
    csv_row = [user['name'], user['birth'], user['gender']] + list(answers.values())
    
    # ★ここに以前のGoogle Drive保存関数を呼び出す
    # save_to_google_drive(csv_row)
    
    print(f"Saved for {user['name']}: {csv_row}")
    return jsonify({"status": "success", "redirect": "/mypage"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))