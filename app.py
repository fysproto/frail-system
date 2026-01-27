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
    # 1. URLパラメータをチェック（ここが重要！）
    # query_paramsにデータが入っていれば、それは「測定終了」のサイン
    ans = st.query_params.to_dict()

    # 2. もしデータ（例えばq12）が届いていたら保存処理へ
    if "q12" in ans:
        # 保存実行
        save_data_to_drive(ans)
        
        # 画面表示
        st.balloons()
        st.success("Google Driveにデータを保存しました。")
        if st.button("最初からやり直す"):
            # URLをクリアしてリロード
            st.query_params.clear()
            st.rerun()
    
    # 3. データがまだ届いていないなら測定画面を表示
    else:
        st.markdown("""
            <style>
                [data-testid="stHeader"], header, footer { display: none !important; }
                .main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
                html, body, [data-testid="stAppViewContainer"] { overflow: hidden !important; position: fixed; width: 100%; height: 100%; }
                iframe { position: fixed; top: 0; left: 0; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 99999; }
            </style>
        """, unsafe_allow_html=True)

        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            # ここでは res = ... は使わず、垂れ流すだけでOK
            components.html(html_content, height=1200)
        except Exception as e:
            st.error(f"システムエラー: {e}")