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
# 1. CẤU HÌNH & SHARED STATE
# ==============================================================================
try:
    FIXED_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    FIXED_GROQ_API_KEY = "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" 

FIXED_CSV_PATH = "res.csv"
LOG_FILE_PATH = "game_logs.csv"  
BACKGROUND_IMAGE_NAME = "background.jpg" 

# DANH SÁCH ADMIN (MIỄN NHIỄM VỚI LUẬT HẾT GIỜ)
ADMIN_IDS = ["250231", "250218"] 

# CẤU HÌNH GAME
MAX_QUESTIONS = 5 
MAX_LIVES = 2

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# --- GLOBAL STATE ---
class SharedGameState:
    def __init__(self):
        self.global_end_time = None 

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
    .main .block-container { background-color: rgba(0, 0, 0, 0.85) !important; padding: 30px !important; border-radius: 25px; border: 2px solid #FFD700; max-width: 800px; }
    h1 { color: #FFD700 !important; font-family: 'Arial Black', sans-serif; text-align: center; }
    h2, h3, p, label, span { color: #FFFFFF !important; }
    div[data-testid="user-message"] { background-color: #FFFFFF !important; color: #004d00 !important; border-radius: 15px 15px 0px 15px !important; padding: 15px !important; font-weight: bold; }
    div[data-testid="assistant-message"] { background-color: #FFFFFF !important; color: #8b0000 !important; border-radius: 15px 15px 15px 0px !important; padding: 15px !important; font-weight: bold; }
    div[data-testid="stMetric"] { background-color: #222222 !important; border: 1px solid #FFD700; border-radius: 10px; }
    div[data-testid="stMetricValue"] { color: #FFD700 !important; }
    .stTextInput input { background-color: #FFFFFF !important; color: #000000 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p { color: #FFD700 !important; }
    #MainMenu, footer, header {visibility: hidden;}
    div.stButton > button:first-child { font-weight: bold; }
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
if "user_start_timestamp" not in st.session_state: st.session_state.user_start_timestamp = None 

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    st.title("🎅 CỔNG ĐĂNG NHẬP")
    profiles = load_data(FIXED_CSV_PATH)

    with st.form("login_form"):
        user_input = st.text_input("Mã số học sinh (hoặc Tên):", placeholder="Ví dụ: 250231...")
        if st.form_submit_button("🚀 BẮT ĐẦU CHƠI NGAY", type="primary"):
            query = user_input.strip()
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                is_vip = selected_user['user_id'] in ADMIN_IDS
                has_lost = check_if_lost(selected_user['user_name'])
                
                # Admin cũng có thể login như user thường ở đây, nhưng không bị chặn nếu thua
                if not is_vip and has_lost:
                    st.error(f"🚫 {selected_user['user_name']} ơi, bạn đã thua rồi! Không thể đăng nhập lại.")
                else:
                    st.session_state.user_info = selected_user
                    st.session_state.question_count = 0
                    st.session_state.wrong_guesses = 0
                    st.session_state.game_status = "PLAYING"
                    st.session_state.messages = []
                    st.session_state.user_start_timestamp = None 
                    
                    if not has_lost: log_activity(selected_user['user_name'], "Login")
                    
                    welcome_msg = f"Ho Ho Ho! Chào **{selected_user['user_name']}**! 🎅\n\n- Con có **{MAX_QUESTIONS} câu hỏi** và **{MAX_LIVES} mạng**.\n- Đoán đúng **HỌ VÀ TÊN** để thắng.\n- **Thời gian sẽ bắt đầu tính khi con gửi tin nhắn đầu tiên!**"
                    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                    st.rerun()

            elif len(matches) > 1: st.warning("⚠️ Có nhiều người trùng tên, nhập MSHS.")
            else: st.error("❌ Không tìm thấy tên.")
    st.stop()

# ==============================================================================
# 6. ADMIN PANEL
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ ADMIN PANEL")
    
    st.markdown("### 🕹️ Điều Khiển Game Toàn Server")
    
    if shared_state.global_end_time:
        remaining = shared_state.global_end_time - time.time()
        if remaining > 0:
            st.info(f"⏳ Game đang chạy! Còn lại: {int(remaining)} giây.")
        else:
            st.error("🛑 Trạng thái: ĐÃ KẾT THÚC.")
    else:
        st.warning("⚪ Timer chưa kích hoạt.")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶️ 5 PHÚT", type="primary", use_container_width=True):
            shared_state.global_end_time = time.time() + 300 
            st.rerun()
    with c2:
        if st.button("🛑 KẾT THÚC NGAY", type="primary", use_container_width=True):
            shared_state.global_end_time = time.time() - 1 
            st.rerun()
    with c3:
        if st.button("⏹️ RESET TIMER", type="secondary", use_container_width=True):
            shared_state.global_end_time = None
            st.rerun()

    initial_uptime = (datetime.datetime.now() - SERVER_START_TIME).total_seconds()
    html_clock = f"""<script>let s={initial_uptime};setInterval(()=>{{s++;let d=new Date(0);d.setSeconds(s);document.getElementById("ut").innerText=d.toISOString().substr(11,8);}},1000);</script><div style="text-align:center;color:#FFD700;margin-top:20px;">Uptime: <span id="ut"></span></div>"""
    components.html(html_clock, height=50)

    if st.button("⬅️ VỀ GAME"):
        st.session_state.is_admin = False
        st.rerun()

    if os.path.exists(LOG_FILE_PATH):
        df_log = pd.read_csv(LOG_FILE_PATH)
        st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
        if st.button("Xóa Log"): 
            os.remove(LOG_FILE_PATH)
            st.rerun()
    st.stop()

# ==============================================================================
# 7. MAIN GAME (USER)
# ==============================================================================
user = st.session_state.user_info
target_gender = get_gender(user['santa_name'])

st.title("🎁 PHÒNG THẨM VẤN")

# --- A. CHECK TIMER (MODIFIED: ADMIN MIỄN NHIỄM) ---
time_remaining_str = "Chưa chạy"

if shared_state.global_end_time:
    remaining_seconds = shared_state.global_end_time - time.time()
    
    if remaining_seconds <= 0:
        # LOGIC MỚI: Kiểm tra xem có phải Admin không
        if user['user_id'] in ADMIN_IDS:
             st.warning("⚠️ CHẾ ĐỘ ADMIN: Game đã hết giờ với người thường, nhưng bạn vẫn được phép thao tác.")
             time_remaining_str = "00:00 (Admin Mode)"
        else:
            # Người thường -> Chặn luôn
            st.error("🛑 ĐÃ HẾT GIỜ! TRÒ CHƠI ĐÃ KẾT THÚC.")
            if st.session_state.game_status == "PLAYING":
                 st.info(f"Đáp án đúng là: {user['santa_name']}")
            st.stop() # Dừng code tại đây
    else:
        mins, secs = divmod(int(remaining_seconds), 60)
        time_remaining_str = f"{mins:02d}:{secs:02d}"

# --- B. USER REAL-TIME CLOCK (JS) ---
start_ts_js = st.session_state.user_start_timestamp if st.session_state.user_start_timestamp else 0

timer_html = f"""
<div style="
    display: flex; justify-content: space-between; 
    background-color: #222; padding: 10px; border-radius: 10px; border: 1px solid #FFD700; margin-bottom: 10px;
">
    <div style="text-align: center; width: 30%;">
        <div style="color: #fff; font-size: 12px;">GỢI Ý</div>
        <div style="color: #FFD700; font-size: 20px; font-weight: bold;">{max(0, MAX_QUESTIONS - st.session_state.question_count)}/{MAX_QUESTIONS}</div>
    </div>
    <div style="text-align: center; width: 30%;">
        <div style="color: #fff; font-size: 12px;">MẠNG</div>
        <div style="color: #FF4500; font-size: 20px; font-weight: bold;">{MAX_LIVES - st.session_state.wrong_guesses}</div>
    </div>
    <div style="text-align: center; width: 40%;">
        <div style="color: #fff; font-size: 12px;">⏱️ BẤM GIỜ</div>
        <div id="user_timer" style="color: #00FF00; font-size: 20px; font-weight: bold;">00:00</div>
    </div>
</div>

<div style="text-align: center; margin-bottom: 10px; color: #FF4500; font-weight: bold;">
    ⏳ ĐẾM NGƯỢC: {time_remaining_str}
</div>

<script>
    let startTimestamp = {start_ts_js}; 
    function updateTimer() {{
        let display = "00:00";
        if (startTimestamp > 0) {{
            let now = Date.now() / 1000;
            let diff = Math.floor(now - startTimestamp);
            if (diff >= 0) {{
                let m = Math.floor(diff / 60);
                let s = Math.floor(diff % 60);
                display = (m < 10 ? "0"+m : m) + ":" + (s < 10 ? "0"+s : s);
            }}
        }}
        document.getElementById("user_timer").innerText = display;
    }}
    setInterval(updateTimer, 1000);
    updateTimer();
</script>
"""
components.html(timer_html, height=120)

with st.sidebar:
    st.title(f"👤 {user['user_name']}")
    if user['user_id'] in ADMIN_IDS:
        if st.button("🛡️ VÀO ADMIN", type="primary"):
            st.session_state.is_admin = True
            st.rerun()
    if st.button("Đăng xuất"):
         st.session_state.user_info = None
         st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.game_status == "WON":
    st.balloons()
    st.success(f"🎉 BẠN ĐÃ THẮNG! SECRET SANTA LÀ: {user['santa_name']}")
    st.stop()
elif st.session_state.game_status == "LOST":
    st.error("☠️ GAME OVER!")
    st.info(f"Đáp án đúng: {user['santa_name']}")
    st.stop()

# --- F. INPUT & AI ---
if prompt := st.chat_input("Nhập câu hỏi hoặc đoán tên..."):
    
    if st.session_state.user_start_timestamp is None:
        st.session_state.user_start_timestamp = time.time()
        st.rerun() 

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        
        system_instruction = f"""
        Bạn là AI Quản trò (mã NPLM). User: {user['user_name']}. Santa: {user['santa_name']} ({target_gender}, MSHS: {user['santa_id']}).
        Status: Hỏi {st.session_state.question_count}/{MAX_QUESTIONS}. Sai {st.session_state.wrong_guesses}/{MAX_LIVES}.
        
        RULES:
        1. [[WIN]]: Đoán ĐÚNG CẢ HỌ TÊN.
        2. [[WRONG]]: Đoán tên cụ thể mà SAI.
        3. [[OK]]: Hỏi gợi ý hợp lệ. Nếu đã dùng {MAX_QUESTIONS} câu gợi ý -> Từ chối.
        4. [[CHAT]]: Chat xã giao.
        """

        messages_payload = [{"role": "system", "content": system_instruction}]
        for m in st.session_state.messages[-6:]: messages_payload.append(m)

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
                else: final_content = "Hết lượt gợi ý rồi! Chỉ được đoán tên thôi."
            else: final_content = full_res.replace("[[CHAT]]", "")

            container.markdown(final_content)
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            
            if action: 
                time.sleep(1)
                st.rerun()
                
    except Exception as e: st.error(f"Lỗi: {e}")
