import streamlit as st
import streamlit.components.v1 as components 
import pandas as pd
from groq import Groq
import os
import datetime
import csv
import time
import base64

# ==============================================================================
# 1. CẤU HÌNH & CONSTANTS
# ==============================================================================
try:
    FIXED_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    FIXED_GROQ_API_KEY = "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" 

FIXED_CSV_PATH = "res.csv"
LOG_FILE_PATH = "game_logs.csv"  
BACKGROUND_IMAGE_NAME = "background.jpg" 

# DANH SÁCH ADMIN (ID)
ADMIN_IDS = ["250231", "250218", "admin"] 

# --- LUẬT CHƠI ---
MAX_QUESTIONS = 5   # 5 Câu hỏi gợi ý
MAX_LIVES = 3       # 3 Mạng
GAME_DURATION = 300 # 5 Phút (300s)

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# --- TRẠNG THÁI GAME TOÀN SERVER ---
class SharedGameState:
    def __init__(self):
        self.status = "WAITING"     
        self.end_timestamp = 0.0    

@st.cache_resource
def get_shared_state():
    return SharedGameState()

shared_state = get_shared_state()

# ==============================================================================
# 2. UTILS
# ==============================================================================
@st.cache_resource
def get_server_start_time():
    return datetime.datetime.now()

SERVER_START_TIME = get_server_start_time()

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
# 3. CSS & GIAO DIỆN (CĂN GIỮA ĐẸP MẮT)
# ==============================================================================
bin_str = get_base64_of_bin_file(BACKGROUND_IMAGE_NAME)
if bin_str:
    page_bg_img = f'''<style>.stApp {{background-image: url("data:image/jpg;base64,{bin_str}"); background-attachment: fixed; background-size: cover;}}</style>'''
else:
    page_bg_img = '''<style>.stApp { background-image: linear-gradient(to bottom, #0f2027, #203a43, #2c5364); }</style>'''
st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
<style>
    /* KHUNG CHÍNH */
    .main .block-container { 
        background-color: rgba(0, 0, 0, 0.85) !important; 
        padding: 30px !important; 
        border-radius: 25px; 
        border: 2px solid #FFD700; 
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
        max-width: 800px; 
    }
    
    /* TYPOGRAPHY CENTERED */
    h1 { 
        color: #FFD700 !important; 
        font-family: 'Arial Black', sans-serif; 
        text-align: center !important; 
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 2px 2px 4px #000;
    }
    
    h2, h3 { 
        color: #FFFFFF !important; 
        text-align: center !important; 
    }
    
    .stAlert { text-align: center !important; }
    
    /* INPUT FIELD */
    .stTextInput input { 
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        font-weight: bold !important; 
        text-align: center !important; /* Căn giữa text lúc nhập */
    }
    
    /* CHAT BUBBLES */
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

    /* BUTTONS */
    div.stButton > button {
        width: 100%;
        font-weight: bold;
    }
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
# 5. MÀN HÌNH ĐĂNG NHẬP (CỔNG CHÀO)
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    st.title("🎄 CỔNG GIÁNG SINH 🎄")
    st.markdown("<h3 style='color: #FFD700; margin-bottom: 20px;'>SECRET SANTA FESTIVE</h3>", unsafe_allow_html=True)
    
    # STATUS CHECK
    if shared_state.status == "WAITING":
        st.info("⏳ CỔNG CHƯA MỞ. VUI LÒNG CHỜ HIỆU LỆNH.")
    elif shared_state.status == "ENDED":
        st.error("🛑 SỰ KIỆN ĐÃ KẾT THÚC.")
    else:
        st.success("🟢 CỔNG ĐANG MỞ! MỜI VÀO!")

    profiles = load_data(FIXED_CSV_PATH)

    with st.form("login_form"):
        st.markdown("<div style='text-align: center; color: white;'>NHẬP DANH TÍNH CỦA BẠN</div>", unsafe_allow_html=True)
        user_input = st.text_input("", placeholder="Mã số học sinh hoặc Tên...") # Label rỗng để đẹp hơn
        
        submitted = st.form_submit_button("🚀 BƯỚC VÀO THẾ GIỚI", type="primary")

        if submitted and user_input:
            query = user_input.strip()
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                is_admin_user = selected_user['user_id'] in ADMIN_IDS
                
                # Logic Gatekeeper
                allow_entry = True
                if not is_admin_user and shared_state.status != "RUNNING":
                    allow_entry = False

                if allow_entry:
                    has_lost = check_if_lost(selected_user['user_name'])
                    if not is_admin_user and has_lost:
                        st.error("⛔ Bạn đã hết lượt tham gia!")
                    else:
                        # LOGIN SUCCESS
                        st.session_state.user_info = selected_user
                        st.session_state.question_count = 0
                        st.session_state.wrong_guesses = 0
                        st.session_state.game_status = "PLAYING"
                        st.session_state.messages = []
                        if not has_lost: log_activity(selected_user['user_name'], "Login")
                        
                        welcome_msg = f"Ho Ho Ho! Chào **{selected_user['user_name']}**! 🎅\n\nLuật chơi mới:\n- ❓ **{MAX_QUESTIONS} câu hỏi** gợi ý.\n- ❤️ **{MAX_LIVES} mạng** (lượt đoán).\n- ⏳ Hãy chú ý đồng hồ đếm ngược!\n\nChúc may mắn!"
                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        st.rerun()
                else:
                    if shared_state.status == "WAITING": st.warning("🚧 Cổng chưa mở.")
                    else: st.error("🏁 Đã hết giờ.")
            elif len(matches) > 1: st.warning("⚠️ Trùng tên, vui lòng nhập MSHS.")
            else: st.error("❌ Không tìm thấy dữ liệu.")
    st.stop()

# ==============================================================================
# 6. ADMIN PANEL
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ CONTROL CENTER")
    st.markdown(f"<div style='text-align: center'>STATUS: <b>{shared_state.status}</b></div>", unsafe_allow_html=True)
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶️ START (5 MIN)", type="primary"):
            shared_state.status = "RUNNING"
            shared_state.end_timestamp = time.time() + GAME_DURATION
            st.rerun()
    with c2:
        if st.button("🛑 STOP GAME", type="primary"):
            shared_state.status = "ENDED"
            shared_state.end_timestamp = time.time() - 1
            st.rerun()
    with c3:
        if st.button("⏹️ RESET"):
            shared_state.status = "WAITING"
            shared_state.end_timestamp = 0
            st.rerun()

    if shared_state.end_timestamp > 0:
        remain = max(0, int(shared_state.end_timestamp - time.time()))
        m, s = divmod(remain, 60)
        st.markdown(f"<h1 style='color: #00FF00 !important'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)

    st.divider()
    if st.button("⬅️ BACK TO GAME"):
        st.session_state.is_admin = False
        st.rerun()

    if os.path.exists(LOG_FILE_PATH):
        with st.expander("VIEW LOGS"):
            df_log = pd.read_csv(LOG_FILE_PATH)
            st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
        if st.button("Clear Logs"): 
            os.remove(LOG_FILE_PATH)
            st.rerun()
    st.stop()

# ==============================================================================
# 7. MAIN GAME INTERFACE (CĂN GIỮA DASHBOARD)
# ==============================================================================
user = st.session_state.user_info
is_vip = user['user_id'] in ADMIN_IDS

# Check Timeout
if shared_state.status == "RUNNING":
    if time.time() > shared_state.end_timestamp:
        if not is_vip:
            st.error("🛑 HẾT GIỜ! GAME OVER.")
            st.stop()
        else: st.toast("Admin Mode: Time is up.")

if not is_vip and shared_state.status != "RUNNING":
    st.error("🛑 KẾT NỐI BỊ NGẮT (ADMIN STOP).")
    if st.button("Thoát"):
        st.session_state.user_info = None
        st.rerun()
    st.stop()

target_gender = get_gender(user['santa_name'])

st.title("🎁 PHÒNG THẨM VẤN")

# --- CUSTOM DASHBOARD (HTML/CSS/JS) ---
# Tạo một khung Dashboard cân đối: [Câu hỏi] - [Đồng hồ] - [Mạng]
q_left = max(0, MAX_QUESTIONS - st.session_state.question_count)
l_left = MAX_LIVES - st.session_state.wrong_guesses
end_ts_js = shared_state.end_timestamp

dashboard_html = f"""
<div style="
    display: flex; 
    justify-content: space-around; 
    align-items: center; 
    background-color: rgba(34, 34, 34, 0.9); 
    border: 2px solid #FFD700; 
    border-radius: 15px; 
    padding: 15px; 
    margin-bottom: 20px;
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
        <div style="color: #FF4500; font-size: 28px; font-weight: 900;">{l_left}<span style="font-size:14px; color:#666">/{MAX_LIVES}</span></div>
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
        
        // Đổi màu khi sắp hết giờ
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
    if user['user_id'] in ADMIN_IDS:
        if st.button("🛡️ VÀO ADMIN", type="primary"):
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
    st.error("☠️ GAME OVER! BẠN ĐÃ HẾT MẠNG.")
    st.info(f"Người tặng quà cho bạn là: **{user['santa_name']}**")
    st.stop()

if st.session_state.game_status == "WON":
    st.balloons()
    st.success(f"🎉 CHÍNH XÁC! SECRET SANTA LÀ: {user['santa_name']}")
    st.stop()

# INPUT AREA
if prompt := st.chat_input("Nhập câu hỏi gợi ý hoặc đoán tên..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        
        system_instruction = f"""
        Bạn là AI Quản trò (NPLM). User: {user['user_name']}. Santa: {user['santa_name']} ({target_gender}, MSHS: {user['santa_id']}).
        Stats: Hỏi {st.session_state.question_count}/{MAX_QUESTIONS}. Sai {st.session_state.wrong_guesses}/{MAX_LIVES}.
        
        RULES:
        1. [[WIN]]: User đoán ĐÚNG CẢ HỌ VÀ TÊN Santa.
        2. [[WRONG]]: User đoán tên cụ thể mà SAI.
        3. [[OK]]: User hỏi gợi ý (về MSHS, giới tính, tên đệm...).
           - Nếu đã hỏi đủ {MAX_QUESTIONS} câu -> Từ chối, bắt đoán tên ngay.
        4. [[CHAT]]: Chat xã giao.
        """

        messages_payload = [{"role": "system", "content": system_instruction}]
        for m in st.session_state.messages[-6:]: messages_payload.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant"):
            container = st.empty()
            full_res = ""
            stream = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages_payload, stream=True)
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    clean = full_res.replace("[[WIN]]","").replace("[[WRONG]]","").replace("[[OK]]","").replace("[[CHAT]]","")
                    container.markdown(clean + "▌")
            
            final_content = full_res
            action = None
            
            if "[[WIN]]" in full_res:
                st.session_state.game_status = "WON"
                log_activity(user['user_name'], "WIN")
                final_content = full_res.replace("[[WIN]]", "")
                action = "WIN"
            elif "[[WRONG]]" in full_res:
                st.session_state.wrong_guesses += 1
                log_activity(user['user_name'], "Guess Wrong")
                final_content = full_res.replace("[[WRONG]]", "")
                if st.session_state.wrong_guesses >= MAX_LIVES:
                    st.session_state.game_status = "LOST"
                    log_activity(user['user_name'], "GAME OVER")
                    action = "LOST"
                else: action = "WRONG"
            elif "[[OK]]" in full_res:
                if st.session_state.question_count < MAX_QUESTIONS:
                    st.session_state.question_count += 1
                    final_content = full_res.replace("[[OK]]", "")
                    action = "OK"
                else: final_content = "Đã hết lượt gợi ý! Hãy đoán tên đi."
            else: final_content = full_res.replace("[[CHAT]]", "")

            container.markdown(final_content)
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            
            if action: 
                time.sleep(1)
                st.rerun()

    except Exception as e: st.error(f"Lỗi: {e}")
