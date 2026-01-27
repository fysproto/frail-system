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
    try:
        creds = st.session_state.credentials
        service = build('drive', 'v3', credentials=creds)
        filename = f"frail_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_metadata = {'name': filename, 'mimeType': 'application/json'}
        media = MediaInMemoryUpload(json.dumps(data, ensure_ascii=False).encode('utf-8'), mimetype='application/json')
        file = service.files().create(body=file_metadata, media_body=media, fields='id,name,webViewLink').execute()
        st.success(f"✅ ファイル保存成功: {filename}")
        st.info(f"File ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        st.error(f"❌ 保存エラー: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

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
            if st.button("📝 測定を開始する", use_container_width=True):
                st.session_state.view = "measure"
                st.session_state.measurement_data = None
                st.rerun()
        with col2:
            st.button("📋 過去の履歴(準備中)", use_container_width=True)

    # --- 測定画面 ---
    elif st.session_state.view == "measure":
        st.markdown("""
            <style>
                [data-testid="stHeader"], header, footer { display: none !important; }
                .main .block-container { padding: 0 !important; margin: 0 !important; }
                iframe { position: fixed; top: 0; left: 0; width: 100vw !important; height: 100vh !important; border: none !important; z-index: 9999; }
            </style>
        """, unsafe_allow_html=True)
        
        # デバッグパネル（開発時のみ表示）
        with st.sidebar:
            st.write("### 🔍 Debug Info")
            st.write(f"View: {st.session_state.view}")
            if st.button("強制的に結果画面へ（テスト用）"):
                st.session_state.view = "result"
                st.session_state.measurement_data = {"test": "data", "is_done": True}
                st.rerun()
        
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # HTMLコンポーネントを表示し、戻り値をキャッチ
            result = components.html(html_content, height=1200, scrolling=False, key="measurement_component")
            
            # デバッグ表示
            st.sidebar.write(f"Component result: {result}")
            st.sidebar.write(f"Result type: {type(result)}")
            
            # データが返ってきたら保存して遷移
            if result is not None:
                st.sidebar.success("✅ データ受信!")
                st.sidebar.json(result)
                
                if isinstance(result, dict) and result.get("is_done"):
                    st.sidebar.info("📦 保存処理開始...")
                    st.session_state.measurement_data = result
                    file_id = save_data_to_drive(result)
                    st.session_state.saved_file_id = file_id
                    st.session_state.view = "result"
                    st.sidebar.success("✅ 画面遷移準備完了")
                    st.rerun()
                
        except FileNotFoundError:
            st.error("index.htmlが見つかりません。ファイルをアップロードしてください。")
        except Exception as e:
            st.error(f"システムエラー: {e}")
            import traceback
            st.code(traceback.format_exc())

    # --- 保存完了画面 ---
    elif st.session_state.view == "result":
        st.balloons()
        st.title("✅ 保存完了")
        st.success("測定データをGoogle Driveに保存しました。")
        
        if st.session_state.get("measurement_data"):
            st.subheader("測定結果")
            data = st.session_state.measurement_data
            col1, col2 = st.columns(2)
            with col1:
                st.metric("握力", f"{data.get('grip', 'N/A')} kg")
                st.metric("BMI", data.get('bmi', 'N/A'))
            with col2:
                if 'q7' in data:
                    st.info(f"Q7: {data['q7']}")
                if 'q12' in data:
                    st.info(f"Q12: {data['q12']}")
            
            st.subheader("📄 全データ")
            st.json(data)
        
        if st.button("マイページへ戻る"):
            st.session_state.view = "mypage"
            st.rerun()
