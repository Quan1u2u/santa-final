import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from groq import Groq
import os
import datetime
import csv
import time
import base64
import json

# ==============================================================================
# 1. CẤU HÌNH & CONSTANTS
# ==============================================================================
try:
    FIXED_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    FIXED_GROQ_API_KEY = "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" 

FIXED_CSV_PATH = "res.csv"
LOG_FILE_PATH = "game_logs.csv"  
CONFIG_FILE_PATH = "game_config.json" # FILE LƯU TRẠNG THÁI GAME TOÀN CỤC
ADMIN_PASSWORD = "admin" 
BACKGROUND_IMAGE_NAME = "background.jpg" 

# DANH SÁCH VIP (ADMIN)
ADMIN_IDS = ["250231", "250218"]

FEMALE_NAMES = [
    "Khánh An", "Bảo Hân", "Lam Ngọc", 
    "Phương Quỳnh", "Phương Nguyên", "Minh Thư"
]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# ==============================================================================
# 2. UTILS & HÀM HỖ TRỢ
# ==============================================================================

# --- QUẢN LÝ THỜI GIAN TOÀN CỤC ---
def get_game_config():
    """Đọc cấu hình game (thời gian kết thúc)"""
    default_end_time = time.time() + 900 # Default 15 mins from now if file missing
    if not os.path.exists(CONFIG_FILE_PATH):
        return {"end_time_epoch": default_end_time, "is_active": True}
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"end_time_epoch": default_end_time, "is_active": True}

def set_game_duration(minutes):
    """Admin set thời gian cho toàn bộ server"""
    end_time = time.time() + (minutes * 60)
    config = {"end_time_epoch": end_time, "is_active": True}
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f)
    return end_time

def stop_game():
    """Admin dừng game ngay lập tức"""
    config = get_game_config()
    config["is_active"] = False
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f)

# --- XỬ LÝ ẢNH & LOG ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def log_activity(user_name, action):
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, mode='w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Thời gian", "Người chơi", "Hành động"])
    with open(LOG_FILE_PATH, mode='a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([time_now, user_name, action])

def check_if_lost(user_name):
    if not os.path.exists(LOG_FILE_PATH): return False
    try:
        df = pd.read_csv(LOG_FILE_PATH)
        losers = df[df['Hành động'] == 'GAME OVER']['Người chơi'].unique()
        return user_name in losers
    except Exception: return False

def get_gender(name):
    for female in FEMALE_NAMES:
        if female.lower() in name.lower(): return "Nữ"
    return "Nam"

def load_data(filepath):
    try:
        if not os.path.exists(filepath): return []    
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip()
        profiles = []
        for index, row in df.iterrows():
            target_name = str(row['TARGET (Ten)']).strip()
            giver_name = str(row['Ten Nguoi Tang']).strip()
            if not target_name or target_name.lower() == 'nan': continue
            profiles.append({
                "search_key": target_name.lower(),
                "user_name": target_name,
                "user_id": str(row['TARGET (MSHS)']).strip(),
                "santa_name": giver_name,
                "santa_id": str(row['Nguoi Tang (MSHS)']).strip()
            })
        return profiles
    except Exception as e:
        st.error(f"Lỗi đọc file CSV: {e}")
        return []

# ==============================================================================
# 3. CSS & GIAO DIỆN
# ==============================================================================
bin_str = get_base64_of_bin_file(BACKGROUND_IMAGE_NAME)
if bin_str:
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{bin_str}");
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
        background-size: cover;
    }}
    </style>
    '''
else:
    page_bg_img = '''<style>.stApp { background-image: linear-gradient(to bottom, #0f2027, #203a43, #2c5364); }</style>'''

st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
<style>
    .main .block-container {
        background-color: rgba(0, 0, 0, 0.85) !important;
        padding: 30px !important;
        border-radius: 25px;
        border: 2px solid #FFD700;
        box-shadow: 0 0 20px rgba(0,0,0,0.8);
        max-width: 800px;
    }
    h1 { color: #FFD700 !important; text-shadow: 2px 2px 4px #000000; font-family: 'Arial Black', sans-serif; text-align: center; }
    h2, h3 { color: #FFFFFF !important; text-shadow: 1px 1px 2px #000; }
    p, label, span { color: #FFFFFF !important; font-weight: 500; }
    
    div[data-testid="user-message"] { background-color: #FFFFFF !important; color: #004d00 !important; border: 3px solid #2e7d32 !important; border-radius: 15px 15px 0px 15px !important; padding: 15px !important; font-weight: bold; }
    div[data-testid="assistant-message"] { background-color: #FFFFFF !important; color: #8b0000 !important; border: 3px solid #d32f2f !important; border-radius: 15px 15px 15px 0px !important; padding: 15px !important; font-weight: bold; }
    
    div[data-testid="stMetric"] { background-color: #222222 !important; border: 1px solid #FFD700; border-radius: 10px; padding: 10px; }
    div[data-testid="stMetricValue"] { color: #FFD700 !important; }
    div[data-testid="stMetricLabel"] { color: #FFFFFF !important; }
    
    .stTextInput input { background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #FFD700 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p { color: #FFD700 !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. KHỞI TẠO STATE
# ==============================================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "user_info" not in st.session_state: st.session_state.user_info = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "question_count" not in st.session_state: st.session_state.question_count = 0 
if "wrong_guesses" not in st.session_state: st.session_state.wrong_guesses = 0  
if "game_status" not in st.session_state: st.session_state.game_status = "PLAYING"

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    st.title("CỔNG ĐĂNG NHẬP GIÁNG SINH")
    st.title("🎅")
    st.markdown("<h3 style='text-align: center; color: white;'>✨ 10 TIN - PTNK Secret Santa ✨</h3>", unsafe_allow_html=True)
    
    profiles = load_data(FIXED_CSV_PATH)

    with st.form("login_form"):
        st.markdown("**Nhập thông tin của bạn:**")
        user_input = st.text_input("Mã số học sinh (hoặc Tên):", placeholder="Ví dụ: 250231...")
        submitted = st.form_submit_button("🚀 BẮT ĐẦU CHƠI NGAY", type="primary")

        if submitted and user_input:
            query = user_input.strip()
            
            # Admin Login
            if query == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.rerun()

            # User Login
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                if check_if_lost(selected_user['user_name']):
                    st.error(f"🚫 {selected_user['user_name']} ơi, bạn đã thua rồi! Không thể đăng nhập lại.")
                else:
                    st.session_state.user_info = selected_user
                    # Reset state
                    st.session_state.question_count = 0
                    st.session_state.wrong_guesses = 0
                    st.session_state.game_status = "PLAYING"
                    st.session_state.messages = []
                    
                    log_activity(selected_user['user_name'], "Login")
                    
                    welcome_msg = f"Ho Ho Ho! Chào **{selected_user['user_name']}**! 🎅\nTa đang giữ bí mật về người tặng quà cho con.\n\nLuật chơi: Con có **3 câu hỏi** và **2 mạng**.\nLưu ý: Phải đoán đúng **HỌ VÀ TÊN** mới thắng nhé!"
                    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                    st.rerun()
            elif len(matches) > 1:
                st.warning("⚠️ Có nhiều người trùng tên, vui lòng nhập MSHS.")
            else:
                st.error("❌ Không tìm thấy tên trong danh sách.")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH ADMIN (QUYỀN LỰC TỐI CAO)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ CONTROL CENTER (ADMIN)")
    
    # --- PANEL ĐIỀU KHIỂN THỜI GIAN ---
    st.markdown("### ⏱️ ĐIỀU KHIỂN THỜI GIAN GAME")
    with st.container(border=True):
        col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
        with col_t1:
            duration_mins = st.number_input("Thời lượng (Phút):", min_value=1, value=15, step=1)
        with col_t2:
            st.write("") 
            st.write("") 
            if st.button("🚀 START / RESET", type="primary", use_container_width=True):
                end_time = set_game_duration(duration_mins)
                st.success(f"Đã set thời gian! Game kết thúc lúc: {datetime.datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
                st.rerun()
        with col_t3:
            st.write("") 
            st.write("")
            if st.button("🛑 STOP GAME", type="secondary", use_container_width=True):
                stop_game()
                st.warning("Đã dừng game!")
                st.rerun()

    # --- SHOW REALTIME COUNTDOWN (PREVIEW) ---
    config = get_game_config()
    end_timestamp = config["end_time_epoch"]
    is_active = str(config["is_active"]).lower()

    # JS Countdown hiển thị cho Admin xem chơi
    admin_timer_html = f"""
    <div style="text-align: center; background: #333; color: #00FF00; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 24px; border: 1px solid #00FF00;">
        ADMIN PREVIEW: <span id="admin_timer">Loading...</span>
    </div>
    <script>
        var endTime = {end_timestamp};
        var isActive = {is_active};
        
        var x = setInterval(function() {{
            if (!isActive) {{
                document.getElementById("admin_timer").innerHTML = "STOPPED";
                return;
            }}
            var now = new Date().getTime() / 1000;
            var distance = endTime - now;
            
            if (distance < 0) {{
                document.getElementById("admin_timer").innerHTML = "TIME UP";
                document.getElementById("admin_timer").style.color = "red";
            }} else {{
                var minutes = Math.floor(distance / 60);
                var seconds = Math.floor(distance % 60);
                document.getElementById("admin_timer").innerHTML = minutes + "m " + seconds + "s ";
            }}
        }}, 1000);
    </script>
    """
    components.html(admin_timer_html, height=70)

    # --- LOGS VÀ THỐNG KÊ ---
    st.markdown("### 📊 THỐNG KÊ REAL-TIME")
    if os.path.exists(LOG_FILE_PATH):
        df_log = pd.read_csv(LOG_FILE_PATH)
        if 'Hành động' in df_log.columns and 'Người chơi' in df_log.columns:
            df_win = df_log[df_log['Hành động'] == 'WIN']
            list_winners = df_win['Người chơi'].unique()
            df_loss = df_log[df_log['Hành động'] == 'GAME OVER']
            list_losers = df_loss['Người chơi'].unique()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("🏆 ĐÃ THẮNG", len(list_winners))
            c2.metric("💀 ĐÃ THUA", len(list_losers))
            c3.metric("👥 TỔNG LOGIN", len(df_log[df_log['Hành động'] == 'Login']['Người chơi'].unique()))
            
            col_list1, col_list2 = st.columns(2)
            with col_list1:
                st.info("🏆 DANH SÁCH THẮNG")
                if len(list_winners) > 0: st.dataframe(list_winners, use_container_width=True, hide_index=True)
            with col_list2:
                st.error("💀 DANH SÁCH THUA")
                if len(list_losers) > 0: st.dataframe(list_losers, use_container_width=True, hide_index=True)

            with st.expander("📝 Xem Chi Tiết Logs"):
                st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
                if st.button("🗑️ XÓA TOÀN BỘ LOG"):
                    os.remove(LOG_FILE_PATH)
                    st.rerun()
        else:
            st.warning("File log lỗi format.")
    else:
        st.info("Chưa có dữ liệu log.")

    st.divider()
    if st.session_state.user_info:
        if st.button("⬅️ QUAY LẠ
