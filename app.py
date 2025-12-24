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

# DANH SÁCH VIP (ADMIN) - Thay bằng MSHS thật của bạn
ADMIN_IDS = ["250231", "250218"]

FEMALE_NAMES = [
    "Khánh An", "Bảo Hân", "Lam Ngọc", 
    "Phương Quỳnh", "Phương Nguyên", "Minh Thư"
]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# ==============================================================================
# 2. UTILS & STATE MANAGEMENT
# ==============================================================================

# --- QUẢN LÝ TRẠNG THÁI GAME ---
# States: WAITING, RUNNING, PAUSED, ENDED

def get_game_config():
    """Đọc cấu hình game"""
    default_config = {
        "end_time_epoch": 0,
        "status": "WAITING", # WAITING, RUNNING, PAUSED, ENDED
        "duration_minutes": 15
    }
    if not os.path.exists(CONFIG_FILE_PATH):
        return default_config
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            return json.load(f)
    except:
        return default_config

def update_game_status(status, duration_mins=None):
    """Admin cập nhật trạng thái"""
    config = get_game_config()
    config["status"] = status
    
    if duration_mins is not None:
        config["duration_minutes"] = duration_mins
        
    if status == "RUNNING":
        # Nếu đang WAITING hoặc ENDED mà chuyển sang RUNNING thì set lại giờ
        # Nếu đang PAUSED sang RUNNING thì giữ nguyên giờ kết thúc (logic đơn giản)
        if config["end_time_epoch"] < time.time(): 
            config["end_time_epoch"] = time.time() + (config["duration_minutes"] * 60)
            
    with open(CONFIG_FILE_PATH, 'w') as f:
        json.dump(config, f)

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
# 3. CSS & VISUAL STYLE (CẢI TIẾN)
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
    page_bg_img = '''<style>.stApp { background-image: linear-gradient(to bottom, #000428, #004e92); }</style>'''

st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
<style>
    /* FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Roboto:wght@400;700&display=swap');

    /* CONTAINER */
    .main .block-container {
        background-color: rgba(20, 20, 20, 0.9) !important;
        padding: 2rem !important;
        border-radius: 20px;
        border: 1px solid #FFD700;
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
        max-width: 850px;
    }

    /* TYPOGRAPHY */
    h1 { 
        color: #FFD700 !important; 
        text-transform: uppercase;
        font-family: 'Roboto', sans-serif;
        text-shadow: 0px 0px 10px rgba(255, 215, 0, 0.5);
        font-size: 2.2rem !important;
        text-align: center;
    }
    h3 { color: #fff !important; text-align: center; font-weight: 300; }

    /* CHAT BUBBLES */
    div[data-testid="user-message"] { 
        background-color: #e3f2fd !important; 
        color: #1565c0 !important; 
        border: none !important;
        border-radius: 15px 15px 0 15px !important; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    div[data-testid="assistant-message"] { 
        background-color: #ffebee !important; 
        color: #b71c1c !important; 
        border: none !important;
        border-radius: 15px 15px 15px 0 !important; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }

    /* METRICS & STATUS */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #2b2b2b, #1a1a1a) !important;
        border: 1px solid #444;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
    div[data-testid="stMetricLabel"] { color: #aaa !important; font-size: 0.8rem !important; }
    div[data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 1.5rem !important; }

    /* INPUT FIELD */
    .stTextInput input { 
        background-color: #fff !important; 
        color: #333 !important; 
        border-radius: 25px !important;
        border: 2px solid #ddd !important;
        padding: 10px 15px !important;
    }
    .stTextInput input:focus { border-color: #FFD700 !important; }

    /* BUTTONS */
    div.stButton > button {
        border-radius: 25px;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    /* HIDE STREAMLIT UI */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. KHỞI TẠO SESSION STATE
# ==============================================================================
if "messages" not in st.session_state: st.session_state.messages = []
if "user_info" not in st.session_state: st.session_state.user_info = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "question_count" not in st.session_state: st.session_state.question_count = 0 
if "wrong_guesses" not in st.session_state: st.session_state.wrong_guesses = 0  
if "game_status" not in st.session_state: st.session_state.game_status = "PLAYING" # Local status (WON/LOST)

# ==============================================================================
# 5. MÀN HÌNH LOGIN
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div style='font-size: 60px; text-align: center;'>🎄</div>", unsafe_allow_html=True)
    
    st.title("CỔNG ĐĂNG NHẬP")
    st.markdown("### ✨ 10 TIN - PTNK SECRET SANTA ✨")
    
    profiles = load_data(FIXED_CSV_PATH)

    with st.container(border=True):
        with st.form("login_form"):
            user_input = st.text_input("Nhập Tên hoặc MSHS:", placeholder="Ví dụ: 250231")
            submitted = st.form_submit_button("🚀 THAM GIA NGAY", type="primary", use_container_width=True)

            if submitted and user_input:
                query = user_input.strip()
                if query == ADMIN_PASSWORD:
                    st.session_state.is_admin = True
                    st.rerun()

                matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
                
                if len(matches) == 1:
                    selected_user = matches[0]
                    if check_if_lost(selected_user['user_name']):
                        st.error(f"🚫 {selected_user['user_name']} đã bị loại khỏi cuộc chơi!")
                    else:
                        st.session_state.user_info = selected_user
                        st.session_state.question_count = 0
                        st.session_state.wrong_guesses = 0
                        st.session_state.game_status = "PLAYING"
                        st.session_state.messages = []
                        log_activity(selected_user['user_name'], "Login")
                        
                        welcome_msg = f"Chào **{selected_user['user_name']}**! 🎅 Ta đang giữ bí mật về người tặng quà cho con.\nLuật chơi: 3 câu hỏi gợi ý và 2 mạng đoán tên. Hãy khôn ngoan!"
                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        st.rerun()
                elif len(matches) > 1:
                    st.warning("⚠️ Có nhiều người trùng tên, hãy nhập MSHS.")
                else:
                    st.error("❌ Không tìm thấy thông tin.")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH ADMIN (CONTROL CENTER)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛠️ TRUNG TÂM ĐIỀU KHIỂN")
    
    # --- GET CONFIG ---
    config = get_game_config()
    current_status = config["status"]
    
    # --- STATUS BOARD ---
    status_color = "green" if current_status == "RUNNING" else ("orange" if current_status == "PAUSED" else "red")
    st.markdown(f"""
    <div style="background-color: #222; padding: 15px; border-radius: 10px; border-left: 5px solid {status_color}; margin-bottom: 20px;">
        <span style="color: #aaa;">CURRENT STATUS:</span> 
        <span style="color: {status_color}; font-weight: bold; font-size: 20px; margin-left: 10px;">{current_status}</span>
    </div>
    """, unsafe_allow_html=True)

    # --- ACTIONS ---
    col_act1, col_act2, col_act3 = st.columns(3)
    
    with col_act1:
        st.subheader("⏱️ Thiết lập")
        new_duration = st.number_input("Phút:", value=15, min_value=1)
        if st.button("▶️ START / RESET GAME", type="primary", use_container_width=True):
            update_game_status("RUNNING", new_duration)
            st.success("Game Started!")
            st.rerun()

    with col_act2:
        st.subheader("⏸️ Điều khiển")
        if st.button("⏸ PAUSE GAME", use_container_width=True):
            update_game_status("PAUSED")
            st.rerun()
        if st.button("▶️ RESUME", use_container_width=True):
            update_game_status("RUNNING") # Resume logic retains end_time in update func
            st.rerun()
            
    with col_act3:
        st.subheader("🛑 Dừng & Chờ")
        if st.button("⏹ STOP & END", type="secondary", use_container_width=True):
            update_game_status("ENDED")
            st.rerun()
        if st.button("⏳ SET WAITING ROOM", use_container_width=True):
            update_game_status("WAITING")
            st.rerun()

    # --- MONITORING ---
    st.divider()
    st.markdown("### 📊 Live Monitor")
    
    if os.path.exists(LOG_FILE_PATH):
        df_log = pd.read_csv(LOG_FILE_PATH)
        if 'Hành động' in df_log.columns:
            m1, m2, m3 = st.columns(3)
            m1.metric("Online Users", len(df_log[df_log['Hành động']=='Login']['Người chơi'].unique()))
            m2.metric("Winners", len(df_log[df_log['Hành động']=='WIN']['Người chơi'].unique()))
            m3.metric("Losers", len(df_log[df_log['Hành động']=='GAME OVER']['Người chơi'].unique()))
            
            with st.expander("📝 Xem Log Chi Tiết"):
                st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
                if st.button("🗑️ Xóa Log"):
                    os.remove(LOG_FILE_PATH)
                    st.rerun()
    
    if st.button("⬅️ THOÁT ADMIN"):
        st.session_state.is_admin = False
        st.rerun()
    st.stop()

# ==============================================================================
# 7. LOGIC NGƯỜI CHƠI & GIAO DIỆN GAME
# ==============================================================================
user = st.session_state.user_info
config = get_game_config()
global_status = config["status"]
end_timestamp = config["end_time_epoch"]

# --- SIDEBAR INFO ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4716/4716328.png", width=80)
    st.markdown(f"### Hello, {user['user_name']}!")
    st.caption(f"ID: {user['user_id']}")
    st.divider()
    if user['user_id'] in ADMIN_IDS:
        if st.button("🛡️ ADMIN PANEL"):
            st.session_state.is_admin = True
            st.rerun()
    if st.button("Đăng xuất"):
        st.session_state.user_info = None
        st.rerun()

# --- CASE 1: WAITING ROOM ---
if global_status == "WAITING":
    st.snow()
    st.markdown("""
    <div style="text-align: center; padding: 50px;">
        <h1 style="color: #fff;">⏳ PHÒNG CHỜ</h1>
        <h3 style="color: #FFD700;">Ông già Noel đang gói quà...</h3>
        <p style="color: #ccc;">Vui lòng đợi Admin bắt đầu trò chơi.</p>
        <div style="font-size: 40px; margin-top: 20px;">🎄🎁❄️</div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(3) # Auto refresh check status
    st.rerun()
    st.stop()

# --- CASE 2: PAUSED ---
if global_status == "PAUSED":
    st.warning("⏸️ TRÒ CHƠI ĐANG TẠM DỪNG! VUI LÒNG ĐỢI...")
    # Vẫn hiện chat history nhưng không cho nhập
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    st.stop()

# --- CASE 3: ENDED ---
if global_status == "ENDED":
    st.error("🏁 TRÒ CHƠI ĐÃ KẾT THÚC!")
    st.stop()

# --- CASE 4: RUNNING (MAIN GAME) ---
# --- HEADER: TIMER & STATS ---
timer_html = f"""
<div style="display: flex; align-items: center; justify-content: space-between; background: #000; padding: 10px 20px; border-radius: 10px; border: 1px solid #FFD700; margin-bottom: 20px;">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="color: #fff; font-weight: bold;">TRẠNG THÁI:</span>
        <span style="background: #00FF00; color: #000; padding: 2px 8px; border-radius: 3px; font-weight: bold; font-size: 12px;">LIVE 🔴</span>
    </div>
    <div style="text-align: right;">
        <div style="color: #aaa; font-size: 10px;">THỜI GIAN CÒN LẠI</div>
        <div id="countdown" style="font-family: 'Orbitron', monospace; color: #FFD700; font-size: 28px; font-weight: bold; letter-spacing: 2px;">--:--</div>
    </div>
</div>

<script>
var countDownDate = {end_timestamp} * 1000;
var x = setInterval(function() {{
  var now = new Date().getTime();
  var distance = countDownDate - now;
  if (distance < 0) {{
    document.getElementById("countdown").innerHTML = "00:00";
    document.getElementById("countdown").style.color = "red";
  }} else {{
    var m = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    var s = Math.floor((distance % (1000 * 60)) / 1000);
    m = m < 10 ? "0" + m : m;
    s = s < 10 ? "0" + s : s;
    document.getElementById("countdown").innerHTML = m + ":" + s;
    if (distance < 60000) {{ document.getElementById("countdown").style.color = "#FF4500"; }}
  }}
}}, 1000);
</script>
"""
components.html(timer_html, height=80)

col_stat1, col_stat2 = st.columns(2)
col_stat1.metric("🔍 GỢI Ý CÒN LẠI", f"{3 - st.session_state.question_count}/3")
col_stat2.metric("💔 MẠNG SỐNG", f"{2 - st.session_state.wrong_guesses}/2")

# --- CHECK GAME END CONDITION (TIME) ---
if time.time() > end_timestamp:
    st.error("⏰ ĐÃ HẾT GIỜ! BẠN KHÔNG KỊP HOÀN THÀNH.")
    st.stop()

# --- CHECK WIN/LOSS ---
if st.session_state.game_status == "WON":
    st.balloons()
    st.success(f"🎉 CHÚC MỪNG! SECRET SANTA CỦA BẠN LÀ: {user['santa_name']}")
    st.image("https://media.giphy.com/media/26tOZ42Mg6pbTUPVS/giphy.gif")
    st.stop()

if st.session_state.game_status == "LOST":
    st.error("💀 GAME OVER! BẠN ĐÃ HẾT MẠNG.")
    st.info(f"Người bí ẩn là: {user['santa_name']}")
    st.stop()

# --- CHAT UI ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- CHAT INPUT & AI LOGIC ---
if prompt := st.chat_input("Hỏi gợi ý hoặc đoán tên (Cần cả Họ Tên)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    target_gender = get_gender(user['santa_name'])
    
    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        
        system_instruction = f"""
        Bạn là AI Quản trò Secret Santa (tên mã NPLM). Tính cách: Lạnh lùng, hơi châm biếm, nhưng công bằng.
        
        DỮ LIỆU BÍ MẬT:
        - Người chơi (User): {user['user_name']}
        - Kẻ Bí Mật (Santa): {user['santa_name']} (Giới tính: {target_gender}, MSHS: {user['santa_id']})
        - Trạng thái: Đã hỏi {st.session_state.question_count}/3. Sai {st.session_state.wrong_guesses}/2.
        
        QUY TẮC TUYỆT ĐỐI - BẠN PHẢI BẮT ĐẦU CÂU TRẢ LỜI BẰNG MỘT TRONG CÁC TOKEN SAU:
        1. [[WIN]] : Nếu user đoán ĐÚNG CẢ HỌ VÀ TÊN (chấp nhận không dấu, viết thường).
        2. [[WRONG]] : Nếu user cố tình đoán tên một người cụ thể nhưng SAI.
        3. [[OK]] : Nếu user đặt câu hỏi gợi ý hợp lệ (Về giới tính, MSHS, tên đệm...).
           - Nếu đã hỏi hết 3 câu -> TỪ CHỐI và dùng [[CHAT]].
        4. [[CHAT]] : Các câu chat xã giao, hoặc từ chối trả lời gợi ý khi hết lượt.

        Lưu ý:
        - KHÔNG tiết lộ tên thật trừ khi [[WIN]].
        - Hỗ trợ toán học về MSHS.
        """

        messages_payload = [{"role": "system", "content": system_instruction}]
        for m in st.session_state.messages[-6:]:
            messages_payload.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages_payload,
                temperature=0.3,
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    clean_preview = full_response.replace("[[WIN]]", "").replace("[[WRONG]]", "").replace("[[OK]]", "").replace("[[CHAT]]", "")
                    message_placeholder.markdown(clean_preview + "▌")
            
            # XỬ LÝ LOGIC SAU KHI AI TRẢ LỜI
            final_content = full_response
            status_update = None
            
            if "[[WIN]]" in full_response:
                st.session_state.game_status = "WON"
                log_activity(user['user_name'], "WIN")
                final_content = full_response.replace("[[WIN]]", "")
                status_update = "WIN"
                
            elif "[[WRONG]]" in full_response:
                st.session_state.wrong_guesses += 1
                log_activity(user['user_name'], "Guess Wrong")
                final_content = full_response.replace("[[WRONG]]", "")
                if st.session_state.wrong_guesses >= 2:
                    st.session_state.game_status = "LOST"
                    log_activity(user['user_name'], "GAME OVER")
                    status_update = "LOST"
                else:
                    status_update = "WRONG"

            elif "[[OK]]" in full_response:
                if st.session_state.question_count < 3:
                    st.session_state.question_count += 1
                    final_content = full_response.replace("[[OK]]", "")
                    status_update = "OK"
                else:
                    final_content = "Hết lượt gợi ý rồi! Đoán đi!" # Fallback nếu AI quên check
            
            else:
                 final_content = full_response.replace("[[CHAT]]", "")

            message_placeholder.markdown(final_content)
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            
            if status_update:
                time.sleep(1)
                st.rerun()

    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
