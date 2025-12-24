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
CONFIG_FILE_PATH = "game_config.json" # Dùng file này để Admin điều khiển toàn server
BACKGROUND_IMAGE_NAME = "background.jpg" 

# DANH SÁCH ADMIN
ADMIN_IDS = ["250231", "250218", "admin"]

# --- LUẬT CHƠI ---
MAX_QUESTIONS = 5  
MAX_GUESSES = 3    

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# ==============================================================================
# 2. UTILS & QUẢN LÝ TRẠNG THÁI (SERVER STATE)
# ==============================================================================

# Hàm đọc/ghi trạng thái game vào file JSON (để Admin điều khiển được tất cả người chơi)
def get_game_config():
    default_config = {
        "end_time_epoch": 0,
        "status": "WAITING", # WAITING, RUNNING, PAUSED, ENDED
        "duration_minutes": 5
    }
    if not os.path.exists(CONFIG_FILE_PATH):
        return default_config
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            return json.load(f)
    except:
        return default_config

def update_game_status(status, duration_mins=None):
    config = get_game_config()
    config["status"] = status
    if duration_mins is not None:
        config["duration_minutes"] = duration_mins
        
    if status == "RUNNING":
        # Nếu đang chạy mà chưa có giờ kết thúc hoặc reset lại
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
    page_bg_img = f'''<style>.stApp {{background-image: url("data:image/jpg;base64,{bin_str}"); background-attachment: fixed; background-size: cover;}}</style>'''
else:
    page_bg_img = '''<style>.stApp { background-image: linear-gradient(to bottom, #0f2027, #203a43, #2c5364); }</style>'''
st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
<style>
    .main .block-container { 
        background-color: rgba(20, 20, 20, 0.9) !important; 
        padding: 2rem !important; 
        border-radius: 20px; 
        border: 1px solid #FFD700; 
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.2);
    }
    h1 { color: #FFD700 !important; text-align: center; text-transform: uppercase; font-family: sans-serif; }
    h3 { color: #fff !important; text-align: center; }
    
    /* Input & Chat Styles */
    .stTextInput input { background-color: #fff !important; color: #333 !important; border-radius: 15px; text-align: center; font-weight: bold;}
    div[data-testid="user-message"] { background-color: #e3f2fd !important; color: #1565c0 !important; border-radius: 15px 15px 0 15px !important; }
    div[data-testid="assistant-message"] { background-color: #ffebee !important; color: #b71c1c !important; border-radius: 15px 15px 15px 0 !important; }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.8) !important; border-right: 1px solid #FFD700; }
    [data-testid="stSidebar"] h1 { font-size: 1.5rem !important; color: #FFD700 !important; }
    
    div.stButton > button { border-radius: 20px; font-weight: bold; width: 100%; }
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

# Lấy config hiện tại từ file
server_config = get_game_config()
global_status = server_config["status"]
end_timestamp = server_config["end_time_epoch"]

# ==============================================================================
# 5. MÀN HÌNH LOGIN (SIDEBAR VERSION)
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    
    # --- Màn hình chính (Landing Page) ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 80px; text-align: center;'>🎄</div>", unsafe_allow_html=True)
    st.title("PTNK SECRET SANTA")
    st.markdown("""
    <div style="text-align: center; color: #ddd; font-style: italic;">
        "Hạnh phúc là khi được chia sẻ những điều bí mật..."
    </div>
    <br>
    <div style="text-align: center; color: #FFD700; font-weight: bold; font-size: 1.2rem; border: 1px solid #FFD700; padding: 20px; border-radius: 10px; background: rgba(0,0,0,0.5);">
        👈 VUI LÒNG ĐĂNG NHẬP Ở CỘT BÊN TRÁI
    </div>
    """, unsafe_allow_html=True)

    # --- Sidebar Form Login ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/260/260250.png", width=100)
        st.title("ĐĂNG NHẬP")
        
        profiles = load_data(FIXED_CSV_PATH)

        with st.form("login_form"):
            user_input = st.text_input("MSHS hoặc Tên:", placeholder="Ví dụ: 250231")
            submitted = st.form_submit_button("🚀 VÀO GAME", type="primary")

            if submitted and user_input:
                query = user_input.strip()
                
                # Check Admin Login
                if query in ADMIN_IDS or query == "admin":
                    st.session_state.is_admin = True
                    st.rerun()

                matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
                
                if len(matches) == 1:
                    selected_user = matches[0]
                    
                    # Logic chặn nếu game chưa bắt đầu (trừ Admin)
                    allow_entry = True
                    if selected_user['user_id'] not in ADMIN_IDS and global_status != "RUNNING":
                         allow_entry = False

                    if allow_entry:
                        if check_if_lost(selected_user['user_name']):
                            st.error(f"🚫 {selected_user['user_name']} đã bị loại!")
                        else:
                            st.session_state.user_info = selected_user
                            st.session_state.question_count = 0
                            st.session_state.wrong_guesses = 0
                            st.session_state.game_status = "PLAYING"
                            st.session_state.messages = []
                            log_activity(selected_user['user_name'], "Login")
                            
                            welcome_msg = f"Chào **{selected_user['user_name']}**! 🎅 Ta đang giữ bí mật về người tặng quà cho con.\n\nLuật chơi: **{MAX_QUESTIONS} câu hỏi gợi ý** và **{MAX_GUESSES} mạng đoán tên**. Hãy tận dụng cơ hội!"
                            st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                            st.rerun()
                    else:
                        if global_status == "WAITING": st.warning("⏳ Phòng chờ đang mở. Đợi Admin bắt đầu!")
                        elif global_status == "ENDED": st.error("🏁 Game đã kết thúc!")
                        else: st.warning("Game chưa bắt đầu.")
                elif len(matches) > 1:
                    st.warning("⚠️ Trùng tên, hãy nhập MSHS.")
                else:
                    st.error("❌ Không tìm thấy thông tin.")
    
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH ADMIN (CONTROL CENTER - PHIÊN BẢN CHI TIẾT)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛠️ TRUNG TÂM ĐIỀU KHIỂN")
    
    current_status = server_config["status"]
    status_color = "green" if current_status == "RUNNING" else ("orange" if current_status == "PAUSED" else "red")
    
    st.markdown(f"""
    <div style="background-color: #222; padding: 15px; border-radius: 10px; border-left: 5px solid {status_color}; margin-bottom: 20px;">
        <span style="color: #aaa;">CURRENT STATUS:</span> 
        <span style="color: {status_color}; font-weight: bold; font-size: 20px; margin-left: 10px;">{current_status}</span>
    </div>
    """, unsafe_allow_html=True)

    col_act1, col_act2, col_act3 = st.columns(3)
    
    with col_act1:
        st.subheader("⏱️ Thiết lập")
        new_duration = st.number_input("Phút:", value=5, min_value=1)
        if st.button("▶️ START / RESET GAME", type="primary"):
            update_game_status("RUNNING", new_duration)
            st.success("Game Started!")
            st.rerun()

    with col_act2:
        st.subheader("⏸️ Điều khiển")
        if st.button("⏸ PAUSE GAME"):
            update_game_status("PAUSED")
            st.rerun()
        if st.button("▶️ RESUME"):
            update_game_status("RUNNING")
            st.rerun()
            
    with col_act3:
        st.subheader("🛑 Dừng & Chờ")
        if st.button("⏹ STOP & END"):
            update_game_status("ENDED")
            st.rerun()
        if st.button("⏳ SET WAITING ROOM"):
            update_game_status("WAITING")
            st.rerun()

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
# 7. LOGIC NGƯỜI CHƠI & GIAO DIỆN GAME (DASHBOARD CENTER)
# ==============================================================================
user = st.session_state.user_info

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

# --- CHECK GLOBAL STATUS ---
if global_status == "WAITING":
    st.snow()
    st.markdown("""<div style="text-align: center;"><h1>⏳ PHÒNG CHỜ</h1><p>Vui lòng đợi Admin bắt đầu trò chơi.</p></div>""", unsafe_allow_html=True)
    time.sleep(3)
    st.rerun()
    st.stop()

if global_status == "PAUSED":
    st.warning("⏸️ TRÒ CHƠI ĐANG TẠM DỪNG!")
    st.stop()

if global_status == "ENDED":
    st.error("🏁 TRÒ CHƠI ĐÃ KẾT THÚC!")
    st.stop()

# --- MAIN DASHBOARD (HTML) ---
st.title("🎁 PHÒNG THẨM VẤN")

q_left = max(0, MAX_QUESTIONS - st.session_state.question_count)
l_left = MAX_GUESSES - st.session_state.wrong_guesses

dashboard_html = f"""
<div style="
    display: flex; justify-content: space-around; align-items: center; 
    background-color: rgba(34, 34, 34, 0.9); border: 2px solid #FFD700; 
    border-radius: 15px; padding: 15px; margin-bottom: 20px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
">
    <div style="text-align: center; width: 30%;">
        <div style="color: #AAA; font-size: 12px; font-weight: bold;">GỢI Ý</div>
        <div style="color: #FFD700; font-size: 28px; font-weight: 900;">{q_left}<span style="font-size:14px; color:#666">/{MAX_QUESTIONS}</span></div>
    </div>
    
    <div style="text-align: center; width: 40%; border-left: 1px solid #444; border-right: 1px solid #444;">
        <div style="color: #AAA; font-size: 12px; font-weight: bold;">THỜI GIAN</div>
        <div id="countdown_timer" style="color: #00FF00; font-size: 32px; font-weight: 900; font-family: monospace;">--:--</div>
    </div>

    <div style="text-align: center; width: 30%;">
        <div style="color: #AAA; font-size: 12px; font-weight: bold;">MẠNG</div>
        <div style="color: #FF4500; font-size: 28px; font-weight: 900;">{l_left}<span style="font-size:14px; color:#666">/{MAX_GUESSES}</span></div>
    </div>
</div>
<script>
    var endTs = {end_timestamp};
    function updateTimer() {{
        var now = Date.now() / 1000;
        var diff = endTs - now;
        var el = document.getElementById("countdown_timer");
        if (diff <= 0) {{ el.innerHTML = "00:00"; el.style.color = "red"; return; }}
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

# Timeout Check
if time.time() > end_timestamp:
    st.error("⏰ ĐÃ HẾT GIỜ! BẠN KHÔNG KỊP HOÀN THÀNH.")
    st.stop()

# Win/Loss Check
if st.session_state.game_status == "WON":
    st.balloons()
    st.success(f"🎉 CHÚC MỪNG! SECRET SANTA CỦA BẠN LÀ: {user['santa_name']}")
    st.stop()

if st.session_state.game_status == "LOST":
    st.error("💀 GAME OVER! BẠN ĐÃ HẾT MẠNG.")
    st.info(f"Người bí ẩn là: {user['santa_name']}")
    st.stop()

# --- CHAT & AI LOGIC ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Hỏi gợi ý hoặc đoán tên..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    target_gender = get_gender(user['santa_name'])
    
    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        
        system_instruction = f"""
        Bạn là AI Quản trò Secret Santa (tên mã NPLM).
        DỮ LIỆU BÍ MẬT:
        - Người chơi (User): {user['user_name']}
        - Kẻ Bí Mật (Santa): {user['santa_name']} (Giới tính: {target_gender}, MSHS: {user['santa_id']})
        - Trạng thái: Đã hỏi {st.session_state.question_count}/{MAX_QUESTIONS}. Sai {st.session_state.wrong_guesses}/{MAX_GUESSES}.
        
        QUY TẮC TUYỆT ĐỐI - BẮT BUỘC DÙNG TOKEN Ở ĐẦU CÂU:
        1. [[WIN]] : Nếu user đoán ĐÚNG CẢ HỌ VÀ TÊN.
        2. [[WRONG]] : Nếu user cố tình đoán tên một người cụ thể nhưng SAI.
        3. [[OK]] : Nếu user đặt câu hỏi gợi ý hợp lệ (Về giới tính, MSHS, tên đệm...).
           - Nếu đã hỏi hết {MAX_QUESTIONS} câu -> TỪ CHỐI và dùng [[CHAT]].
        4. [[CHAT]] : Các câu chat xã giao, hoặc từ chối gợi ý khi hết lượt.
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
                if st.session_state.wrong_guesses >= MAX_GUESSES:
                    st.session_state.game_status = "LOST"
                    log_activity(user['user_name'], "GAME OVER")
                    status_update = "LOST"
                else:
                    status_update = "WRONG"

            elif "[[OK]]" in full_response:
                if st.session_state.question_count < MAX_QUESTIONS:
                    st.session_state.question_count += 1
                    final_content = full_response.replace("[[OK]]", "")
                    status_update = "OK"
                else:
                    final_content = "Hết lượt gợi ý rồi! Đoán đi!"
            
            else:
                 final_content = full_response.replace("[[CHAT]]", "")

            message_placeholder.markdown(final_content)
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            
            if status_update:
                time.sleep(1)
                st.rerun()

    except Exception as e:
        st.error(f"Lỗi: {str(e)}")
