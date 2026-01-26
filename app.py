import streamlit as st
import streamlit.components.v1 as components
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

# --- 設定 ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# 【重要】現在の実際のアプリURLに固定しました
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# --- 認証ロジック ---
def authenticate_google():
    if 'credentials' not in st.session_state:
        # Secretsから情報を読み込む
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

        # Googleログイン後の処理
        if "code" in st.query_params:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            st.query_params.clear()
            st.rerun()
            return st.session_state.credentials
        
        # ログインボタンの表示
        else:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.title("フレイル測定アプリ")
            st.write("プロトタイプデモ画面へようこそ。")
            st.write("動作確認にはGoogleアカウントでのログインが必要です。")
            st.link_button("Googleアカウントでログイン", auth_url)
            return None
            
    return st.session_state.credentials

# --- Google Drive保存機能 ---
def save_data_to_drive(data, filename):
    creds = st.session_state.credentials
    service = build('drive', 'v3', credentials=creds)
    
    file_metadata = {'name': filename, 'mimeType': 'application/json'}
    media = MediaInMemoryUpload(json.dumps(data).encode('utf-8'), mimetype='application/json')
    
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# --- メイン処理 ---
creds = authenticate_google()

if creds:
    # 1. 究極の余白削除 & 全画面固定
    st.markdown("""
        <style>
            /* 1. ツールバー、ヘッダー、フッターを物理的に削除 */
            [data-testid="stHeader"], header, footer { display: none !important; }
            
            /* 2. アプリ全体の余白をゼロにし、位置を最上部に強制固定 */
            .main .block-container {
                padding: 0 !important;
                margin: 0 !important;
                max-width: 100% !important;
            }
            
            /* 3. Streamlitの「外枠」を動かなくする */
            html, body, [data-testid="stAppViewContainer"] {
                overflow: hidden !important;
                position: fixed;
                width: 100%;
                height: 100%;
            }

            /* 4. HTML表示領域（iframe）を全画面にし、スクロールをここだけに集中させる */
            iframe {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw !important;
                height: 100vh !important;
                border: none !important;
                z-index: 99999;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. index.html の読み込み
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # 3. アドレスバー対策：スマホで全画面に見えるようにメタタグを注入
        # これにより、少し動かすとアドレスバーが引っ込みやすくなります
        mobile_fix = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
        full_content = mobile_fix + html_content

        # 4. 表示
        st.components.v1.html(
            full_content,
            height=1200, # 中身より少し長くしておく
            scrolling=True
        )
        
    except FileNotFoundError:
        st.error("index.html が見つかりません。")