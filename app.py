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

# --- 認証（成功したロジック） ---
def authenticate_google():
    if 'credentials' not in st.session_state:
        client_config = {
            "web": {
                "client_id": st.secrets["google_client_id"],
                "client_secret": st.secrets["google_client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
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
            st.stop()
    return st.session_state.credentials

# --- 保存処理（成功したロジック） ---
def save_data_to_drive(data):
    creds = st.session_state.credentials
    service = build('drive', 'v3', credentials=creds)
    filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # CSV形式で整理して保存
    csv_content = "item,value\n"
    for k, v in data.items():
        csv_content += f"{k},{v}\n"
        
    media = MediaInMemoryUpload(csv_content.encode('utf-8-sig'), mimetype='text/csv')
    service.files().create(body={'name': filename}, media_body=media).execute()

# --- URLからのデータ受取ロジック（バイパス案） ---
if st.query_params.get("done") == "1":
    raw_data = st.query_params.get("data")
    if raw_data:
        try:
            # 受信データを保存して結果画面へ
            save_data_to_drive(json.loads(raw_data))
            st.query_params.clear()
            st.session_state.view = "result"
            st.rerun()
        except Exception as e:
            st.error(f"保存エラー: {e}")

creds = authenticate_google()

if creds:
    if "view" not in st.session_state:
        st.session_state.view = "mypage"

    # --- マイページ ---
    if st.session_state.view == "mypage":
        st.title("🏠 マイページ")
        st.write("健康状態をチェックしましょう。")
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
            </style>
        """, unsafe_allow_html=True)
        
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            # 画面を表示（heightを大きめにして見切れ防止）
            components.html(html_content, height=1000)
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