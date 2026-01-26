import streamlit as st
import streamlit.components.v1 as components
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

# --- 設定 ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# --- 認証 ---
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
            st.link_button("Googleアカウントでログイン", auth_url)
            return None
    return st.session_state.credentials

def save_data_to_drive(data):
    creds = st.session_state.credentials
    service = build('drive', 'v3', credentials=creds)
    filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    file_metadata = {'name': filename, 'mimeType': 'application/json'}
    media = MediaInMemoryUpload(json.dumps(data, ensure_ascii=False).encode('utf-8'), mimetype='application/json')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return filename

creds = authenticate_google()

if creds:
    # 赤枠エラーを防ぐために CSS を少し緩める
    st.markdown("""
        <style>
            [data-testid="stHeader"], header, footer { display: none !important; }
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            /* iframeの設定を極限までシンプルに */
            iframe { 
                width: 100vw !important; height: 100vh !important; 
                border: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # データを一時的に保持する場所
    if "final_data" not in st.session_state:
        st.session_state.final_data = None

    # HTMLの表示
    if st.session_state.final_data is None:
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # 戻り値をセッションに格納
            res = components.html(html_content, height=1200)
            if res:
                st.session_state.final_data = res
                st.rerun()
        except FileNotFoundError:
            st.error("index.htmlが見つかりません。")
    
    # データが届いた後の処理
    else:
        st.balloons()
        with st.spinner("ドライブに保存中..."):
            fname = save_data_to_drive(st.session_state.final_data)
            st.success(f"### 保存完了！\nファイル: {fname}")
            if st.button("次の測定へ"):
                st.session_state.final_data = None
                st.rerun()