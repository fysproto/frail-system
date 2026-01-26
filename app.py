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

# --- Google認証 ---
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
    # 状態管理
    if "is_saved" not in st.session_state:
        st.session_state.is_saved = False
    
    # CSS: 赤枠警告を隠し、測定画面に没入させる
    st.markdown("""
        <style>
            [data-testid="stHeader"], header, footer { display: none !important; }
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            iframe { width: 100vw !important; height: 100vh !important; border: none !important; }
            [data-testid="stNotification"], .stAlert { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # まだ保存が完了していない（測定中）
    if not st.session_state.is_saved:
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_code = f.read()
            
            # 3問の測定画面を表示
            res = components.html(html_code, height=1200)
            
            # HTML側の「最後の次へ」ボタンでデータが送られてきた場合
            if res is not None and isinstance(res, dict) and "done" in res:
                save_data_to_drive(res)
                st.session_state.is_saved = True
                st.rerun()
        except Exception as e:
            st.error(f"システムエラー: {e}")

    # 保存完了後の画面
    else:
        st.balloons()
        st.markdown("<div style='text-align:center; padding: 50px 0;'>", unsafe_allow_html=True)
        st.write("## 🎉 測定結果を保存しました")
        st.write("Googleドライブにデータが保管されました。")
        if st.button("マイページへ戻る"):
            st.session_state.is_saved = False # リセットして戻る（擬似）
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)