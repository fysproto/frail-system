import streamlit as st
import streamlit.components.v1 as components
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google_auth_oauthlib.flow import Flow
from datetime import datetime

# --- 設定 ---
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# --- ① 認証ロジック（成功版） ---
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
            flow = Flow.from_client_config(cfg, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            # URLを綺麗にしてリロード
            st.query_params.clear()
            st.rerun()
        else:
            flow = Flow.from_client_config(cfg, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt="consent")
            st.title("フレイル測定アプリ")
            st.link_button("Googleアカウントでログイン", auth_url)
            st.stop()
    return st.session_state.credentials

# --- ② 保存ロジック（知見を投入） ---
def save_to_drive(data_dict, service):
    # 日本語の項目名マッピング（任意で増やしてね）
    label_map = {
        "q7": "歩行速度低下",
        "q12": "地域活動参加",
        "grip": "握力",
        "bmi": "BMI"
    }
    
    csv = "項目,値\n"
    csv += f"測定日時,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    for k, v in data_dict.items():
        label = label_map.get(k, k) # マップになければIDをそのまま使う
        csv += f"{label},{v}\n"
    
    media = MediaInMemoryUpload(csv.encode("utf-8-sig"), mimetype="text/csv") # Excelで見れるようUTF-8-SIG
    name = f"frail_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    service.files().create(body={"name": name}, media_body=media).execute()

# 認証実行
creds = auth()
service = build("drive", "v3", credentials=creds)

# --- ③ URLからのデータ受信（ハイディのバイパス案） ---
if st.query_params.get("done") == "1":
    data_str = st.query_params.get("data")
    if data_str:
        try:
            # 受信データを保存
            save_to_drive(json.loads(data_str), service)
            # URLをクリアして結果画面へ
            st.query_params.clear()
            st.session_state.view = "result"
            st.rerun()
        except Exception as e:
            st.error(f"データ処理エラー: {e}")

# --- ④ 画面遷移管理 ---
if "view" not in st.session_state:
    st.session_state.view = "mypage"

if st.session_state.view == "mypage":
    st.title("🏠 マイページ")
    st.write("健康チェックを開始しましょう。")
    if st.button("📏 測定を開始する", use_container_width=True):
        st.session_state.view = "measure"
        st.rerun()

elif st.session_state.view == "measure":
    # 測定画面：元のUIを最大化表示
    st.markdown("<style>[data-testid='stHeader'],header,footer{display:none;}.main .block-container{padding:0;}</style>", unsafe_allow_html=True)
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
        components.html(html, height=1200)
    except FileNotFoundError:
        st.error("index.html が見つかりません。")

elif st.session_state.view == "result":
    st.balloons()
    st.title("✅ 測定・保存完了")
    st.success("結果を Google Drive に保存しました。")
    if st.button("マイページへ戻る"):
        st.session_state.view = "mypage"
        st.rerun()