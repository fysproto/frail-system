import streamlit as st
import streamlit.components.v1 as components
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

# --- 設定 ---
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "https://frail-system-fnpbjmywss88x6zh2a9egn.streamlit.app/"

st.set_page_config(page_title="フレイル予防システム", layout="centered")

# =========================
# Drive 保存関数（デバッグ用メッセージ付き）
# =========================
def save_data_to_drive(data):
    if "credentials" not in st.session_state:
        st.error("認証情報が見つかりません。再ログインしてください。")
        return False
    try:
        service = build("drive", "v3", credentials=st.session_state.credentials)
        filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # CSVデータ作成
        csv = "item,value\n"
        for k, v in data.items():
            csv += f"{k},{v}\n"
            
        media = MediaInMemoryUpload(csv.encode("utf-8"), mimetype="text/csv")
        service.files().create(
            body={"name": filename},
            media_body=media
        ).execute()
        return True
    except Exception as e:
        st.error(f"Drive保存中にエラーが発生しました: {e}")
        return False

# =========================
# 【重要】最優先：データ持ち帰り検知
# =========================
# 認証チェックの前に、まずデータがあるか確認する
if st.query_params.get("done") == "1":
    raw_data = st.query_params.get("data")
    if raw_data:
        # データをセッションに退避
        st.session_state["_pending_data"] = json.loads(raw_data)
        # URLを綺麗にする（重要：これをしないと保存が何度も走る）
        st.query_params.clear()
        st.rerun()

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
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            flow.fetch_token(code=st.query_params["code"])
            st.session_state.credentials = flow.credentials
            st.query_params.clear()
            st.rerun()
        else:
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)
            auth_url, _ = flow.authorization_url(prompt="consent")
            st.title("フレイル測定アプリ")
            st.link_button("Googleアカウントでログイン", auth_url)
            return None
    return st.session_state.credentials

creds = authenticate_google()

# =========================
# 保存実行ロジック
# =========================
if creds and "_pending_data" in st.session_state:
    data_to_save = st.session_state["_pending_data"]
    # セッションから消去（保存失敗してもループさせない）
    del st.session_state["_pending_data"]
    
    if save_data_to_drive(data_to_save):
        st.session_state.view = "result" # 保存成功したらリザルトへ
        st.rerun()

# =========================
# 画面表示制御
# =========================
if creds:
    if "view" not in st.session_state:
        st.session_state.view = "mypage"

    if st.session_state.view == "mypage":
        st.title("🏠 マイページ")
        if st.button("📏 測定を開始する", use_container_width=True):
            st.session_state.view = "measure"
            st.rerun()

    elif st.session_state.view == "measure":
        st.markdown("<style>[data-testid='stHeader'],header,footer{display:none;}.main .block-container{padding:0;}</style>", unsafe_allow_html=True)
        with open("index.html", "r", encoding="utf-8") as f:
            html = f.read()
        components.html(html, height=1200)

    elif st.session_state.view == "result":
        st.balloons()
        st.title("✅ 保存完了")
        st.success("Google Driveに測定結果を保存しました！")
        if st.button("マイページへ戻る"):
            st.session_state.view = "mypage"
            st.rerun()