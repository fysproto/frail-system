import streamlit as st
import streamlit.components.v1 as components
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# =========================
# Google 認証
# =========================
def authenticate_google():
    if "credentials" not in st.session_state:
        client_config = {
            "web": {
                "client_id": st.secrets["google_client_id"],
                "client_secret": st.secrets["google_client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        }

        if "code" in st.query_params:
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
            )
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            st.query_params.clear()
            st.rerun()
        else:
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
            )
            auth_url, _ = flow.authorization_url(prompt="consent")
            st.title("フレイル測定アプリ")
            st.link_button("Googleアカウントでログイン", auth_url)
            return None

    return st.session_state.credentials

# =========================
# Drive 保存
# =========================
def save_data_to_drive(data: dict):
    service = build("drive", "v3", credentials=st.session_state.credentials)

    filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    csv = "key,value\n"
    for k, v in data.items():
        csv += f"{k},{v}\n"

    media = MediaInMemoryUpload(csv.encode("utf-8"), mimetype="text/csv")

    service.files().create(
        body={"name": filename},
        media_body=media
    ).execute()

# =========================
# メイン
# =========================
creds = authenticate_google()
if not creds:
    st.stop()

st.title("🏠 マイページ")
st.write("健康状態をチェックしましょう。")

if st.button("📏 測定を開始する", use_container_width=True):
    st.session_state.view = "measure"

if st.session_state.get("view") == "measure":
    st.markdown(
        """
        <style>
        [data-testid="stHeader"], header, footer { display:none !important; }
        .main .block-container { padding:0 !important; margin:0 !important; }
        iframe {
            position:fixed;
            top:0; left:0;
            width:100vw !important;
            height:100vh !important;
            border:none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    result = components.html(html, height=1200)

    # ★ ここが肝：iframe から値が返った瞬間
    if result is not None:
        save_data_to_drive(result)
        st.session_state.view = None
        st.success("測定データを保存しました")
        st.balloons()
