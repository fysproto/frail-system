import streamlit as st
import streamlit.components.v1 as components
import json
import os
import qrcode
from io import BytesIO
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

# --- 設定（ここはあなたの環境に合わせてあるわ） ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
REDIRECT_URI = "https://frail-app-demo-gjy9srwec5ajdfhytfjxct.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# --- QRコードを表示する関数（これを忘れてたでしょ？） ---
def show_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf, caption="スマホでスキャンして検証", width=200)

# --- 認証ロジック ---
def authenticate_google():
    if 'credentials' not in st.session_state:
        if "code" in st.query_params:
            flow = Flow.from_client_secrets_file(
                'credentials.json', scopes=SCOPES, redirect_uri=REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            st.query_params.clear()
        else:
            # ログインしていない時にQRコードとボタンを出す
            st.info("スマートフォンで検証する場合は、以下のQRコードをスキャンしてね。")
            show_qr_code(REDIRECT_URI) # ここで呼び出してるわ
            
            flow = Flow.from_client_secrets_file(
                'credentials.json', scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.link_button("Googleアカウントでログイン", auth_url)
            return None
    return st.session_state.credentials

# 実行
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