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
CONFIG_FILE_PATH = "game_config.json"
VIP_FILE_PATH = "vip_users.json"
BACKGROUND_IMAGE_NAME = "background.jpg"
PROGRESS_FILE = "user_progress.json" # File lưu trạng thái chống Reload

ADMIN_IDS = ["250231", "250218"]

# --- LUẬT CHƠI ---
STD_MAX_QUESTIONS = 3   
STD_MAX_LIVES = 1       
VIP_MAX_QUESTIONS = 5  
VIP_MAX_LIVES = 3       
DEFAULT_DURATION = 15  

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# ==============================================================================
# 2. UTILS (HÀM HỖ TRỢ)
# ==============================================================================

# --- [NEW] HÀM LƯU TIẾN ĐỘ CHỐNG RELOAD ---
def load_user_progress(user_id):
    """Đọc tiến độ của user từ file json"""
    if not os.path.exists(PROGRESS_FILE):
        return None
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(str(user_id))
    except:
        return None

def save_user_progress(user_id, q_count, w_guesses):
    """Lưu tiến độ hiện tại của user"""
    data = {}
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {}
    
    data[str(user_id)] = {
        "question_count": q_count,
        "wrong_guesses": w_guesses
    }
    
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- CÁC HÀM CŨ ---
def get_vip_list():
    if not os.path.exists(VIP_FILE_PATH): return []
    try:
        with open(VIP_FILE_PATH, 'r') as f: return json.load(f)
    except: return []

def add_vip_user(mshs):
    vips = get_vip_list()
    if mshs not in vips:
        vips.append(str(mshs).strip())
        with open(VIP_FILE_PATH, 'w') as f: json.dump(vips, f)
        return True
    return False

def get_game_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        return {"end_time_epoch": 0, "is_active": False}
    try:
        with open(CONFIG_FILE_PATH, 'r') as f: return json.load(f)
    except: return {"end_time_epoch": 0, "is_active": False}

def set_game_duration(minutes):
    end_time = time.time() + (minutes * 60)
    config = {"end_time_epoch": end_time, "is_active": True}
    with open(CONFIG_FILE_PATH, 'w') as f: json.dump(config, f)
    return end_time

def stop_game():
    config = get_game_config()
    config["is_active"] = False
    with open(CONFIG_FILE_PATH, 'w') as f: json.dump(config, f)

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
    except: return False

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
            if not target_name or target_name.lower() == 'nan': continue
            profiles.append({
                "search_key": target_name.lower(),
                "user_name": target_name,
                "user_id": str(row['TARGET (MSHS)']).strip(),
                "santa_name": str(row['Ten Nguoi Tang']).strip(),
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
    page_bg_img = f'''<style>.stApp {{background-image: url("data:image/jpg;base64,{bin_str}"); background-attachment: fixed; background-size: cover;}}</style>'''
else:
    page_bg_img = '''<style>.stApp { background-image: linear-gradient(to bottom, #000000, #1a1a1a); }</style>'''
st.markdown(page_bg_img, unsafe_allow_html=True)
st.markdown("""
<style>
    .main .block-container { 
        background-color: rgba(0, 0, 0, 1) !important; 
        padding: 30px !important; 
        border-radius: 25px; 
        border: 2px solid #FFD700; 
        box-shadow: 0 0 20px rgba(255, 215, 0, 1);
        max-width: 800px; 
    }
    h1 { 
        color: #FFD700 !important; 
        font-family: 'Arial Black', sans-serif; 
        text-align: center !important; 
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 2px 2px 4px #000;
    }
    h2, h3 { color: #FFFFFF !important; text-align: center !important; }
    .stAlert { text-align: center !important; }
    .stTextInput input { 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        text-align: center !important; 
    }
    div[data-testid="user-message"] { 
        background-color: #FFFFFF !important; 
        color: #004d00 !important; 
        border-radius: 15px 15px 0px 15px !important; 
        padding: 15px !important; 
        font-weight: bold; 
    }
    div[data-testid="assistant-message"] { 
        background-color: #FFFFFF !important; 
        color: #8b0000 !important; 
        border-radius: 15px 15px 15px 0px !important; 
        padding: 15px !important; 
        font-weight: bold; 
    }
    div.stButton > button { width: 100%; font-weight: bold; }
    div[data-testid="stMetric"] { background-color: #222222 !important; border: 1px solid #FFD700; border-radius: 10px; padding: 10px; }
    div[data-testid="stMetricValue"] { color: #FFD700 !important; }
    div[data-testid="stMetricLabel"] { color: #FFFFFF !important; }
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
if "current_max_q" not in st.session_state: st.session_state.current_max_q = STD_MAX_QUESTIONS
if "current_max_l" not in st.session_state: st.session_state.current_max_l = STD_MAX_LIVES
if "is_vip_user" not in st.session_state: st.session_state.is_vip_user = False

current_config = get_game_config()
is_game_active = current_config["is_active"]
game_end_time = current_config["end_time_epoch"]
current_time = time.time()

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP (CỔNG CHÀO)
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    st.title("🎄 CỔNG GIÁNG SINH 🎄")
    st.title("🎅")
    st.markdown("<h3 style='text-align: center; color: white;'>✨ 10 TIN - PTNK Secret Santa ✨</h3>", unsafe_allow_html=True)
    
    # --- PHẦN 1: TRẠNG THÁI CỔNG (HEADER) ---
    if not is_game_active:
        # ⏳ CHỜ: Xanh Dương Đậm
        st.markdown(
            """<div style="background-color: #003366; color: #FFFFFF; padding: 15px 20px; border-radius: 12px; border: 2px solid #3399FF; text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            ⏳ CỔNG CHƯA MỞ ⏳
            </div>""", unsafe_allow_html=True)
    elif current_time > game_end_time:
        # 🛑 KẾT THÚC: Đỏ Đậm
        st.markdown(
            """<div style="background-color: #8B0000; color: #FFFFFF; padding: 15px 20px; border-radius: 12px; border: 2px solid #FF6666; text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            🛑 SỰ KIỆN ĐÃ KẾT THÚC (HẾT GIỜ)
            </div>""", unsafe_allow_html=True)
    else:
        # 🟢 ĐANG MỞ: Xanh Lá Đậm
        st.markdown(
            """<div style="background-color: #006400; color: #FFFFFF; padding: 15px 20px; border-radius: 12px; border: 2px solid #33FF33; text-align: center; font-weight: bold; font-size: 18px; margin-bottom: 20px; box-shadow: 0 0 15px rgba(50, 255, 50, 0.4);">
            🟢 CỔNG ĐANG MỞ! MỜI VÀO!
            </div>""", unsafe_allow_html=True)

    profiles = load_data(FIXED_CSV_PATH)

    with st.form("login_form"):
        st.markdown("**Nhập thông tin của bạn:**")
        user_input = st.text_input("Mã số học sinh (hoặc Tên):", placeholder="Ví dụ: 250218...")
        submitted = st.form_submit_button("🚀 BƯỚC VÀO THẾ GIỚI", type="primary")

        if submitted and user_input:
            query = user_input.strip()
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                user_id = selected_user['user_id']
                is_admin_user = user_id in ADMIN_IDS

                # --- [NEW] CHECK TIME UP NGAY TẠI CỔNG ---
                if not is_admin_user and current_time > game_end_time:
                     st.markdown("""<div style="background-color: #8B0000; color: #FFFFFF; padding: 15px; border-radius: 10px; border: 2px solid #FF0000; text-align: center; font-weight: bold; margin-top: 10px;">
                        ⏳ ĐÃ HẾT GIỜ! KHÔNG THỂ ĐĂNG NHẬP.
                        </div>""", unsafe_allow_html=True)
                     st.stop()

                # Check VIP
                vip_list = get_vip_list()
                is_vip = user_id in vip_list

                # Logic Gatekeeper
                allow_entry = True
                if not is_admin_user:
                    if not is_game_active: allow_entry = False

                if allow_entry:
                    has_lost = check_if_lost(selected_user['user_name'])
                    if not is_admin_user and has_lost:
                        # ⛔ BÁO LỖI: HẾT LƯỢT
                        st.markdown("""<div style="background-color: #8B0000; color: #FFFFFF; padding: 15px; border-radius: 10px; border: 2px solid #FF0000; text-align: center; font-weight: bold; margin-top: 10px;">
                            ⛔ BẠN ĐÃ HẾT LƯỢT THAM GIA!<br>Hẹn gặp lại mùa sau nhé.
                            </div>""", unsafe_allow_html=True)
                    else:
                        # LOGIN SUCCESS
                        st.session_state.user_info = selected_user
                        st.session_state.game_status = "PLAYING"
                        st.session_state.is_vip_user = is_vip
                        
                        # --- [NEW] LOAD TIẾN ĐỘ CHỐNG RELOAD ---
                        saved_progress = load_user_progress(user_id)
                        if saved_progress:
                            st.session_state.question_count = saved_progress.get("question_count", 0)
                            st.session_state.wrong_guesses = saved_progress.get("wrong_guesses", 0)
                            st.toast(f"🔄 Đã khôi phục tiến độ cũ.", icon="💾")
                        else:
                            st.session_state.question_count = 0
                            st.session_state.wrong_guesses = 0

                        st.session_state.messages = []

                        if is_vip:
                            st.session_state.current_max_q = VIP_MAX_QUESTIONS
                            st.session_state.current_max_l = VIP_MAX_LIVES
                            limit_msg = f"🌟 **VIP MEMBER DETECTED** 🌟\n- ❓ **{VIP_MAX_QUESTIONS} câu hỏi**\n- ❤️ **{VIP_MAX_LIVES} mạng**"
                        else:
                            st.session_state.current_max_q = STD_MAX_QUESTIONS
                            st.session_state.current_max_l = STD_MAX_LIVES
                            limit_msg = f"Luật chơi thường:\n- ❓ **{STD_MAX_QUESTIONS} câu hỏi**\n- ❤️ **{STD_MAX_LIVES} mạng**"

                        if not has_lost: log_activity(selected_user['user_name'], "Login")
                        
                        welcome_msg = f"Ho Ho Ho! Chào **{selected_user['user_name']}**! 🎅\n\n{limit_msg}\n\n👉 **Bạn đang ở: {st.session_state.question_count}/{st.session_state.current_max_q} câu hỏi**\n⏳ Hãy chú ý đồng hồ!\n\nChúc may mắn!"
                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        st.rerun()
                else:
                    if not is_game_active: 
                        # 🚧 Cảnh báo chưa mở
                         st.markdown("""<div style="background-color: #995500; color: #FFFFFF; padding: 15px; border-radius: 10px; border: 2px solid #FFCC00; text-align: center; font-weight: bold; margin-top: 10px;">
                            🚧 CỔNG CHƯA MỞ! VUI LÒNG QUAY LẠI SAU.
                            </div>""", unsafe_allow_html=True)
                    else: 
                        # 🏁 Cảnh báo hết giờ
                        st.markdown("""<div style="background-color: #8B0000; color: #FFFFFF; padding: 15px; border-radius: 10px; border: 2px solid #FF0000; text-align: center; font-weight: bold; margin-top: 10px;">
                            🏁 SỰ KIỆN ĐÃ KẾT THÚC. KHÔNG THỂ ĐĂNG NHẬP.
                            </div>""", unsafe_allow_html=True)

            elif len(matches) > 1: 
                # ⚠️ CẢNH BÁO TRÙNG TÊN
                st.markdown("""<div style="background-color: #995500; color: #FFFFFF; padding: 15px; border-radius: 10px; border: 2px solid #FFCC00; text-align: center; font-weight: bold; margin-top: 10px;">
                    ⚠️ PHÁT HIỆN TRÙNG TÊN!<br>Vui lòng nhập chính xác <b>Mã Số Học Sinh</b>.
                    </div>""", unsafe_allow_html=True)
            else: 
                # ❌ KHÔNG TÌM THẤY
                st.markdown("""<div style="background-color: #8B0000; color: #FFFFFF; padding: 15px; border-radius: 10px; border: 2px solid #FF0000; text-align: center; font-weight: bold; margin-top: 15px;">
                    ❌ KHÔNG TÌM THẤY DỮ LIỆU NGƯỜI CHƠI.<br>Vui lòng kiểm tra lại Tên hoặc MSHS.
                    </div>""", unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# 6. ADMIN PANEL
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ TRUNG TÂM CHỈ HUY 🛡️(ADMIN)")
    
    st.markdown("### ⏱️ ĐIỀU KHIỂN THỜI GIAN GAME")
    with st.container(border=True):
        col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
        with col_t1:
            duration_mins = st.number_input("Thời lượng (Phút):", min_value=1, value=DEFAULT_DURATION, step=1)
        with col_t2:
            st.write("") 
            st.write("") 
            if st.button("🚀 START / RESET", type="primary", use_container_width=True):
                end_time = set_game_duration(duration_mins)
                st.success(f"Game End: {datetime.datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
                st.rerun()
        with col_t3:
            st.write("") 
            st.write("")
            if st.button("🛑 STOP GAME", type="secondary", use_container_width=True):
                stop_game()
                st.warning("Đã dừng game!")
                st.rerun()

    st.markdown("### 💎 NẠP VIP")
    with st.container(border=True):
        col_vip1, col_vip2 = st.columns([3, 1])
        with col_vip1:
            vip_mshs_input = st.text_input("Nhập MSHS cần lên VIP:", placeholder="Ví dụ: 250123")
        with col_vip2:
            st.write("")
            st.write("")
            if st.button("🌟 NÂNG VIP", type="primary", use_container_width=True):
                if vip_mshs_input:
                    add_vip_user(vip_mshs_input)
                    st.success(f"Đã thêm VIP: {vip_mshs_input}")
                else:
                    st.error("Chưa nhập MSHS.")

    config = get_game_config()
    end_timestamp = config["end_time_epoch"]
    is_active_js = str(config["is_active"]).lower()

    admin_timer_html = f"""
    <div style="text-align: center; background: #333; color: #00FF00; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 24px; border: 1px solid #00FF00;">
        ADMIN PREVIEW: <span id="admin_timer">Loading...</span>
    </div>
    <script>
        var endTime = {end_timestamp};
        var isActive = {is_active_js};
        
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

    st.divider()
    if st.button("⬅️ BACK TO GAME"):
        st.session_state.is_admin = False
        st.rerun()

    st.markdown("### 📊 THỐNG KÊ")
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
            
            with st.expander("📝 Xem Chi Tiết Logs"):
                st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
                if st.button("🗑️ XÓA TOÀN BỘ LOG"):
                    os.remove(LOG_FILE_PATH)
                    st.rerun()
    st.stop()

# ==============================================================================
# 7. MAIN GAME INTERFACE
# ==============================================================================
user = st.session_state.user_info
is_vip_admin = user['user_id'] in ADMIN_IDS

LIMIT_Q = st.session_state.current_max_q
LIMIT_L = st.session_state.current_max_l

config = get_game_config()
is_active = config["is_active"]
end_timestamp = config["end_time_epoch"]

# --- [NEW] REAL-TIME CHECK: NẾU HẾT GIỜ KHI ĐANG CHƠI THÌ CHẶN LUÔN ---
if not is_vip_admin and is_active and time.time() > end_timestamp:
    st.markdown(
        """<div style="background-color: #8B0000; color: white; padding: 20px; border-radius: 15px; text-align: center; border: 3px solid red; font-size: 20px; font-weight: bold; margin-bottom: 20px;">
        ⏰ <b>ĐÃ HẾT GIỜ!</b><br>
        Sự kiện đã kết thúc trong khi bạn đang chơi.<br>
        Rất tiếc, kết quả không được ghi nhận thêm.
        </div>""", 
        unsafe_allow_html=True
    )
    st.stop()
# ------------------------------------------------------------------------

# Check Admin Force Stop
if not is_vip_admin and not is_active:
    st.markdown("""<div style="background-color: #8B0000; color: white; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid red;">🛑 KẾT NỐI BỊ NGẮT (ADMIN STOP).</div>""", unsafe_allow_html=True)
    if st.button("Thoát"):
        st.session_state.user_info = None
        st.rerun()
    st.stop()

target_gender = get_gender(user['santa_name'])

st.title("🎁 PHÒNG THAM VẤN TÌM RA SECRET SANTA")

# --- DASHBOARD ---
q_left = max(0, LIMIT_Q - st.session_state.question_count)
l_left = LIMIT_L - st.session_state.wrong_guesses
end_ts_js = end_timestamp if is_active else 0

dashboard_html = f"""
<div style="display: flex; justify-content: space-around; align-items: center; background-color: #222222; border: 2px solid #FFD700; border-radius: 15px; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
    <div style="text-align: center; width: 30%;">
        <div style="color: #AAA; font-size: 12px; font-weight: bold;">GỢI Ý</div>
        <div style="color: #FFD700; font-size: 28px; font-weight: 900;">{q_left}<span style="font-size:14px; color:#666">/{LIMIT_Q}</span></div>
    </div>
    
    <div style="text-align: center; width: 40%; border-left: 1px solid #444; border-right: 1px solid #444;">
        <div style="color: #AAA; font-size: 12px; font-weight: bold;">THỜI GIAN</div>
        <div id="countdown_timer" style="color: #00FF00; font-size: 32px; font-weight: 900; font-family: monospace;">--:--</div>
    </div>

    <div style="text-align: center; width: 30%;">
        <div style="color: #AAA; font-size: 12px; font-weight: bold;">MẠNG</div>
        <div style="color: #FF4500; font-size: 28px; font-weight: 900;">{l_left}<span style="font-size:14px; color:#666">/{LIMIT_L}</span></div>
    </div>
</div>
<script>
    var endTs = {end_ts_js};
    function updateTimer() {{
        var now = Date.now() / 1000;
        var diff = endTs - now;
        var el = document.getElementById("countdown_timer");
        
        if (diff <= 0) {{
            el.innerHTML = "00:00";
            el.style.color = "red";
            return;
        }}
        
        var m = Math.floor(diff / 60);
        var s = Math.floor(diff % 60);
        el.innerHTML = (m<10?"0"+m:m) + ":" + (s<10?"0"+s:s);
        
        if (diff < 60) el.style.color = "orange";
        if (diff < 10) el.style.color = "red";
    }}
    setInterval(updateTimer, 1000);
    updateTimer();
</script>
"""
components.html(dashboard_html, height=100)

# SIDEBAR & MENU
with st.sidebar:
    st.markdown(f"<h2 style='text-align:center'>👤 {user['user_name']}</h2>", unsafe_allow_html=True)
    if st.session_state.is_vip_user:
        st.markdown("<div style='text-align:center; color:gold; font-weight:bold; border:1px solid gold; padding:5px; border-radius:5px;'>🌟 VIP MEMBER</div>", unsafe_allow_html=True)
    
    if user['user_id'] in ADMIN_IDS:
        if st.button("🛡️ ADMIN", type="primary"):
            st.session_state.is_admin = True
            st.rerun()
    st.divider()
    if st.button("Đăng xuất"):
         st.session_state.user_info = None
         st.rerun()

# CHAT HISTORY
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# CHECK GAME OVER / WIN
if st.session_state.game_status == "LOST":
    st.markdown("""<div style="background-color: #
