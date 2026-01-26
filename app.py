import streamlit as st
import streamlit.components.v1 as components
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

# --- 設定 ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
# ★ここをご自身のStreamlitのURLに合わせてください
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# --- 認証ロジック ---
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
            st.query_params.clear()
            st.rerun()
        else:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.title("フレイル測定アプリ")
            st.write("測定を開始するには、下のボタンからログインしてください。")
            st.link_button("Googleアカウントでログイン", auth_url)
            return None
    return st.session_state.credentials

# --- Google Drive保存機能 ---
def save_data_to_drive(data):
    creds = st.session_state.credentials
    service = build('drive', 'v3', credentials=creds)
    filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    file_metadata = {'name': filename, 'mimeType': 'application/json'}
    media = MediaInMemoryUpload(json.dumps(data, ensure_ascii=False).encode('utf-8'), mimetype='application/json')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return filename

# --- メイン処理 ---
creds = authenticate_google()

if creds:
    # データ受取用のプレースホルダー
    placeholder = st.empty()

    # スマホ用CSS（外枠の固定）
    st.markdown("""
        <style>
            [data-testid="stHeader"], header, footer { display: none !important; }
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            section.main { overflow: hidden !important; }
            iframe { 
                position: fixed; top: 0; left: 0; width: 100vw !important; height: 100vh !important; 
                border: none !important; z-index: 999; pointer-events: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)

    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        # HTMLを表示
        with placeholder.container():
            response_data = components.html(html_content, height=2000)

        # データが届いたら保存処理
        if response_data:
            placeholder.empty() # HTML画面を消去
            with st.spinner("Googleドライブに保存中..."):
                fname = save_data_to_drive(response_data)
                st.balloons()
                st.success(f"### 🎉 測定完了！\nデータを保存しました: {fname}")
                if st.button("もう一度測定する"):
                    st.rerun()
            
    except FileNotFoundError:
        st.error("index.html が見つかりません。")