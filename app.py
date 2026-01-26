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
    # 1. 上の空白を「マイナスの余白」で無理やり消し去るCSS
    st.markdown("""
        <style>
            /* 1. 全体の余白とスクロール設定 */
            html, body, [data-testid="stAppViewContainer"] {
                overflow: hidden !important;
                height: 100vh !important;
            }
            /* 2. 上部の見えない余白を完全に削る(ネガティブマージン) */
            .main .block-container {
                padding-top: 0 !important;
                padding-bottom: 0 !important;
                margin-top: -50px !important; /* ここで上に引き上げます */
                max-width: 100% !important;
            }
            /* 3. メニューバーやヘッダーを物理的に消滅させる */
            header[data-testid="stHeader"] {
                display: none !important;
            }
            [data-testid="stVerticalBlock"] {
                gap: 0 !important;
            }
            
            /* 4. iframeを画面いっぱいに */
            iframe {
                width: 100vw !important;
                height: 100vh !important;
                border: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. index.html の読み込み
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # 3. 高さをしっかり取って、内部スクロールを確実に有効にする
        st.components.v1.html(
            html_content,
            height=1200,   # もし下がまだ足りなければ1500に増やしてください
            scrolling=True # これでスマホでの指の動きが中身に伝わります
        )
        
    except FileNotFoundError:
        st.error("index.html が見つかりません。")