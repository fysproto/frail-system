import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google_auth_oauthlib.flow import Flow
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="保存テスト", layout="centered")

def auth():
    if "credentials" not in st.session_state:
        cfg = {
            "web": {
                "client_id": st.secrets["google_client_id"],
                "client_secret": st.secrets["google_client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        }
        if "code" in st.query_params:
            flow = Flow.from_client_config(cfg, SCOPES, REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            st.query_params.clear()
            st.rerun()
        else:
            flow = Flow.from_client_config(cfg, SCOPES, REDIRECT_URI)
            url, _ = flow.authorization_url(prompt="consent")
            st.link_button("Googleでログイン", url)
            st.stop()
    return st.session_state.credentials

creds = auth()
service = build("drive", "v3", credentials=creds)

st.title("強制保存テスト")

if st.button("今すぐ保存する"):
    csv = "key,value\nTEST,OK\n"
    media = MediaInMemoryUpload(csv.encode("utf-8"), mimetype="text/csv")
    name = f"frail_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    service.files().create(body={"name": name}, media_body=media).execute()
    st.success("保存した。Driveを見て。")
