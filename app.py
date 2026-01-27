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
        # 最新版の判定方法
        if "code" in st.query_params:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            # パラメータ削除
            for key in list(st.query_params.keys()):
                del st.query_params[key]
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
    
    # CSV形式に整形
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = "timestamp," + ",".join(data.keys()) + "\n"
    values = f"{timestamp}," + ",".join([str(v) for v in data.values()]) + "\n"
    csv_body = header + values
    
    filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    file_metadata = {'name': filename, 'mimeType': 'text/csv'}
    media = MediaInMemoryUpload(csv_body.encode('utf-8'), mimetype='text/csv')
    service.files().create(body=file_metadata, media_body=media).execute()

# --- メインロジック ---
creds = authenticate_google()

if creds:
    # ★ 核心：URLパラメータからのデータ復元
    # .get() を直接使うのが最新の安全な書き方
    if st.query_params.get("done") == "1":
        raw_data = st.query_params.get("data")
        if raw_data:
            try:
                save_data_to_drive(json.loads(raw_data))
                # クエリパラメータを全削除してリセット
                for key in list(st.query_params.keys()):
                    del st.query_params[key]
                st.session_state.view = "result"
                st.rerun()
            except Exception as e:
                st.error(f"保存失敗: {e}")

    if "view" not in st.session_state:
        st.session_state.view = "mypage"

    if st.session_state.view == "mypage":
        st.title("🏠 マイページ")
        if st.button("📏 測定を開始する", use_container_width=True):
            st.session_state.view = "measure"
            st.rerun()

    elif st.session_state.view == "measure":
        st.markdown("<style>[data-testid='stHeader'],header,footer{display:none;}.main .block-container{padding:0;}</style>", unsafe_allow_html=True)
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            components.html(html_content, height=1200)
        except Exception as e:
            st.error(f"HTML読み込みエラー: {e}")

    elif st.session_state.view == "result":
        st.balloons()
        st.title("✅ 保存完了")
        if st.button("マイページへ戻る"):
            st.session_state.view = "mypage"
            st.rerun()