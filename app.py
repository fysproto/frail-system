import streamlit as st
import streamlit.components.v1 as components
import json
import csv
import io
from datetime import datetime
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

# ================================
# Google Drive / OAuth 設定
# ================================
SCOPES = ['https://www.googleapis.com/auth/drive.file']
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# ================================
# Google 認証
# ================================
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

# ================================
# Drive 保存（CSV）
# ================================
def save_csv_to_drive(data: dict):
    service = build('drive', 'v3', credentials=st.session_state.credentials)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["key", "value"])
    for k, v in data.items():
        writer.writerow([k, v])

    csv_bytes = output.getvalue().encode('utf-8-sig')

    filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    media = MediaInMemoryUpload(csv_bytes, mimetype='text/csv')
    file_metadata = {
        'name': filename,
        'mimeType': 'text/csv'
    }

    service.files().create(body=file_metadata, media_body=media).execute()

# ================================
# Custom Component 定義
# ================================
frail_component = components.declare_component(
    "frail_component",
    path="./frail_component"  # ← frontend build ディレクトリ
)

# ================================
# メイン処理
# ================================
creds = authenticate_google()

if creds:
    if "view" not in st.session_state:
        st.session_state.view = "mypage"

    # --- マイページ ---
    if st.session_state.view == "mypage":
        st.title("🏠 マイページ")
        st.write("健康状態をチェックしましょう。")
        if st.button("📏 測定を開始する", use_container_width=True):
            st.session_state.view = "measure"
            st.rerun()

    # --- 測定画面 ---
    elif st.session_state.view == "measure":
        st.markdown("""
            <style>
                [data-testid=\"stHeader\"], header, footer { display: none !important; }
                .main .block-container { padding: 0 !important; }
            </style>
        """, unsafe_allow_html=True)

        result = frail_component()

        if result is not None and result.get("is_done") is True:
            save_csv_to_drive(result)
            st.session_state.view = "result"
            st.rerun()

    # --- 完了画面 ---
    elif st.session_state.view == "result":
        st.balloons()
        st.title("✅ 保存完了")
        st.success("測定データをGoogle DriveにCSV保存しました")
        if st.button("マイページへ戻る"):
            st.session_state.view = "mypage"
            st.rerun()
