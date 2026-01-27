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
    service.files().create(body=file_metadata, media_body=media).execute()

creds = authenticate_google()

if creds:
    # ★ ここが生命線：URLパラメータに回答データ（q12など）が入っているかチェック
    params = st.query_params.to_dict()

    if "view" not in st.session_state:
        st.session_state.view = "mypage"

    # もしURLに「測定完了(is_done)」のフラグが立っていたら、強制的に保存画面へ
    if params.get("is_done") == "true":
        save_data_to_drive(params)
        st.query_params.clear() # URLを掃除
        st.session_state.view = "result"
        st.rerun()

    # --- マイページ ---
    if st.session_state.view == "mypage":
        st.title("🏠 マイページ")
        st.write("ようこそ！あなたの健康状態をチェックしましょう。")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📏 測定を開始する", use_container_width=True):
                st.session_state.view = "measure"
                st.rerun()
        with col2:
            st.button("📋 過去の履歴（準備中）", use_container_width=True)

    # --- 測定画面 ---
    elif st.session_state.view == "measure":
        st.markdown("""
            <style>
                [data-testid="stHeader"], header, footer { display: none !important; }
                .main .block-container { padding: 0 !important; margin: 0 !important; }
                iframe { position: fixed; top: 0; left: 0; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 9999; }
            </style>
        """, unsafe_allow_html=True)
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            components.html(html_content, height=2000)
        except Exception as e:
            st.error(f"システムエラー: {e}")

    # --- 保存完了画面 ---
    elif st.session_state.view == "result":
        st.balloons()
        st.title("✅ 保存完了")
        st.success("測定データをGoogle Driveに保存しました。")
        if st.button("マイページへ戻る"):
            st.session_state.view = "mypage"
            st.rerun()