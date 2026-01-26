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
            return st.session_state.credentials
        else:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.title("フレイル測定アプリ")
            st.write("Googleアカウントでのログインが必要です。")
            st.link_button("Googleアカウントでログイン", auth_url)
            return None
    return st.session_state.credentials

def save_data_to_drive(data, filename):
    creds = st.session_state.credentials
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': filename, 'mimeType': 'application/json'}
    media = MediaInMemoryUpload(json.dumps(data, ensure_ascii=False).encode('utf-8'), mimetype='application/json')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

creds = authenticate_google()

if creds:
    if "is_finished" not in st.session_state:
        st.session_state.is_finished = False

    st.markdown("""
        <style>
            [data-testid="stHeader"], header, footer { display: none !important; }
            .main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
            html, body, [data-testid="stAppViewContainer"] { overflow: hidden !important; position: fixed; width: 100%; height: 100%; }
            iframe { position: fixed; top: 0; left: 0; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 99999; }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.is_finished:
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # HTMLからのデータ（Message）を受け取る
            res = components.html(html_content, height=1200, scrolling=True)
            
            # データが届いたら保存して完了画面へ
            if res and isinstance(res, dict) and res.get("done"):
                filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                save_data_to_drive(res, filename)
                st.session_state.is_finished = True
                st.rerun()

        except FileNotFoundError:
            st.error("index.html が見つかりません。")
    else:
        st.balloons()
        st.markdown("<div style='text-align:center; padding-top:100px;'>", unsafe_allow_html=True)
        st.success("### 測定データを保存しました")
        if st.button("もう一度測定する"):
            st.session_state.is_finished = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)