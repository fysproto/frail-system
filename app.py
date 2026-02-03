import streamlit as st
import streamlit.components.v1 as components
import json
import urllib.parse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

# --- 設定（RenderのURLに合わせて変更して） ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
# RenderのデプロイURLをここに反映させてね
REDIRECT_URI = "https://your-render-app-url.onrender.com/" 

st.set_page_config(page_title="フレイル予防支援システム", layout="centered")

# --- セッション状態の初期化 ---
if 'view' not in st.session_state:
    st.session_state.view = "login"
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# --- Google認証ロジック ---
def authenticate_google():
    if 'credentials' not in st.session_state:
        client_config = {
            "web": {
                "client_id": st.secrets["google_client_id"],
                "project_id": "frail-app-project",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": st.secrets["google_client_secret"],
                "redirect_uris": [REDIRECT_URI]
            }
        }
        if "code" in st.query_params:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            st.session_state.view = "profile" # 認証後はプロフィール入力へ
            st.rerun()
        else:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.link_button("Googleでログインして開始", auth_url)
            return False
    return True

# --- Google Drive保存ロジック (CSV/フォルダ管理) ---
def save_data_to_drive(measurement_data):
    creds = st.session_state.credentials
    service = build('drive', 'v3', credentials=creds)

    # 1. フォルダ「fraildata」の管理
    folder_name = "fraildata"
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    folders = service.files().list(q=query, fields="files(id)").execute().get('files', [])
    
    if not folders:
        folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')
    else:
        folder_id = folders[0].get('id')

    # 2. データの平滑化（CSV一行分）
    u = st.session_state.user_info
    timestamp = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    
    # CSV列順: タイムスタンプ, 名前, 性別, 生年月日, 郵便番号, 指輪っか, Q1-15, 握力, 身長, 体重, BMI
    row = [
        timestamp,
        u.get('name'),
        u.get('gender'), # 1:男, 2:女
        u.get('birth'),
        u.get('zipcode'),
        measurement_data.get('finger', ''),
        *[measurement_data.get(f'q{i}', '') for i in range(1, 16)],
        measurement_data.get('grip', ''),
        measurement_data.get('height', ''),
        measurement_data.get('weight', ''),
        measurement_data.get('bmi', '')
    ]
    csv_content = ",".join(map(str, row)) + "\n"

    # 3. ファイル保存 (個人名と日付をファイル名に)
    filename = f"測定_{u.get('name')}_{datetime.now().strftime('%Y%m%d')}.csv"
    media = MediaInMemoryUpload(csv_content.encode('utf-8'), mimetype='text/csv')
    service.files().create(body={'name': filename, 'parents': [folder_id]}, media_body=media).execute()

# --- メインロジック ---
if not authenticate_google():
    st.stop()

# --- 1. プロフィール入力 & 同意画面 ---
if st.session_state.view == "profile":
    st.title("📋 基本情報の登録")
    st.write("測定を始める前に、あなたの情報を教えてください。")
    
    with st.form("profile_form"):
        name = st.text_input("お名前")
        gender = st.radio("性別", ["男性", "女性"], horizontal=True)
        birth = st.date_input("生年月日", min_value=datetime(1920, 1, 1))
        zipcode = st.text_input("郵便番号 (例: 123-4567)")
        
        st.markdown("---")
        st.subheader("📝 同意事項")
        st.info("入力されたデータは、フレイル予防の研究および自治体による健康支援、アドバイスの提供に利用されます。")
        agree_sys = st.checkbox("システム提供者へのデータ提供に同意する")
        agree_gov = st.checkbox("お住まいの自治体へのデータ提供に同意する")
        
        submit = st.form_submit_button("測定画面へ進む")
        
        if submit:
            if not (name and zipcode):
                st.error("お名前と郵便番号を入力してください。")
            elif not (agree_sys and agree_gov):
                st.error("全ての同意事項にチェックを入れてください。")
            else:
                st.session_state.user_info = {
                    "name": name,
                    "gender": "1" if gender == "男性" else "2",
                    "birth": str(birth),
                    "zipcode": zipcode
                }
                st.session_state.view = "measure"
                st.rerun()

# --- 2. 測定画面（index.htmlの呼び出し） ---
elif st.session_state.view == "measure":
    # 測定終了後のデータ受け取り
    if "data" in st.query_params:
        try:
            raw_data = st.query_params["data"]
            measurement_data = json.loads(urllib.parse.unquote(raw_data))
            if measurement_data.get("is_done"):
                save_data_to_drive(measurement_data)
                st.session_state.view = "complete"
                st.rerun()
        except Exception as e:
            st.error(f"データ保存エラー: {e}")

    # 性別をクエリパラメータとしてHTMLに渡す
    g_param = st.session_state.user_info.get('gender', '1')
    
    st.markdown("""
        <style>
            [data-testid="stHeader"], header, footer { display: none !important; }
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            iframe { position: fixed; top: 0; left: 0; width: 100vw !important; height: 100vh !important; border: none !important; }
        </style>
    """, unsafe_allow_html=True)
    
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        # index.html内でこの性別を参照して判定閾値を変える
        components.html(html_content, height=2000) # 十分な高さを確保
    except FileNotFoundError:
        st.error("index.htmlが見つかりません。")

# --- 3. 完了画面 ---
elif st.session_state.view == "complete":
    st.balloons()
    st.title("✅ 測定完了")
    st.success(f"{st.session_state.user_info['name']}さんの測定データをGoogle Driveの「fraildata」フォルダに保存しました。")
    st.write("自治体のトレーナーからのアドバイスをお待ちください。")
    if st.button("トップに戻る"):
        st.session_state.view = "profile"
        st.rerun()