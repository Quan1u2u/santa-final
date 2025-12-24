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

# --- CẬP NHẬT LUẬT CHƠI TẠI ĐÂY ---
MAX_QUESTIONS = 5  # Tăng lên 5 câu hỏi
MAX_LIVES = 3      # Tăng lên 3 mạng
GAME_DURATION = 300 # Thời gian chơi mỗi vòng (giây) = 5 phút

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# --- TRẠNG THÁI GAME TOÀN SERVER ---
class SharedGameState:
    def __init__(self):
        self.status = "WAITING"     # WAITING, RUNNING, ENDED
        self.end_timestamp = 0.0    # Thời điểm kết thúc (Unix timestamp)

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
    
    /* COUNTDOWN STYLE */
    .countdown-box {
        background-color: #222; 
        color: #FF4500; 
        padding: 10px; 
        border-radius: 10px; 
        text-align: center; 
        font-size: 24px; 
        font-weight: bold; 
        border: 2px solid #FF4500;
        margin-bottom: 20px;
        animation: pulse 1s infinite;
    }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255, 69, 0, 0.7); } 70% { box-shadow: 0 0 10px 10px rgba(255, 69, 0, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 69, 0, 0); } }
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
    st.title("🎅 CỔNG ĐĂNG NHẬP")
    
    # STATUS INDICATOR
    if shared_state.status == "WAITING":
        st.info("⏳ GAME CHƯA BẮT ĐẦU. VUI LÒNG CHỜ ADMIN.")
    elif shared_state.status == "ENDED":
        st.error("🛑 GAME ĐÃ KẾT THÚC.")
    else:
        st.success("🟢 CỔNG ĐANG MỞ! VÀO NGAY!")

    profiles = load_data(FIXED_CSV_PATH)

    with st.form("login_form"):
        user_input = st.text_input("Mã số học sinh (hoặc Tên):", placeholder="Ví dụ: 250231...")
        if st.form_submit_button("🚀 BẮT ĐẦU CHƠI", type="primary"):
            query = user_input.strip()
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                is_admin_user = selected_user['user_id'] in ADMIN_IDS
                
                # --- CHECK QUYỀN VÀO ---
                allow_entry = True
                if not is_admin_user:
                    if shared_state.status != "RUNNING": allow_entry = False

                if allow_entry:
                    has_lost = check_if_lost(selected_user['user_name'])
                    if not is_admin_user and has_lost:
                        st.error("🚫 Bạn đã thua rồi!")
                    else:
                        st.session_state.user_info = selected_user
                        st.session_state.question_count = 0
                        st.session_state.wrong_guesses = 0
                        st.session_state.game_status = "PLAYING"
                        st.session_state.messages = []
                        
                        if not has_lost: log_activity(selected_user['user_name'], "Login")
                        
                        # --- CẬP NHẬT TEXT CHÀO MỪNG VỚI LUẬT MỚI ---
                        welcome_msg = f"Chào **{selected_user['user_name']}**! 🎅\n\nLuật mới:\n- ❓ **{MAX_QUESTIONS} câu hỏi**.\n- ❤️ **{MAX_LIVES} mạng**.\n- ⏳ **Đồng hồ đếm ngược** bên trên!\nChúc may mắn!"
                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        st.rerun()
                else:
                    if shared_state.status == "WAITING": st.warning("Game chưa bắt đầu.")
                    else: st.error("Game đã kết thúc.")

            elif len(matches) > 1: st.warning("⚠️ Trùng tên, nhập MSHS.")
            else: st.error("❌ Không tìm thấy.")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH ADMIN
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ ADMIN PANEL")
    
    st.write(f"Trạng thái: **{shared_state.status}**")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶️ START (5 PHÚT)", type="primary", use_container_width=True):
            shared_state.status = "RUNNING"
            shared_state.end_timestamp = time.time() + GAME_DURATION # Set thời gian kết thúc
            st.rerun()
    with c2:
        if st.button("🛑 KẾT THÚC NGAY", type="primary", use_container_width=True):
            shared_state.status = "ENDED"
            shared_state.end_timestamp = time.time() - 1 # Trick để countdown về 0 ngay
            st.rerun()
    with c3:
        if st.button("⏹️ RESET STATUS", use_container_width=True):
            shared_state.status = "WAITING"
            shared_state.end_timestamp = 0
            st.rerun()

    # Admin Dashboard Countdown
    if shared_state.end_timestamp > 0:
        remain = max(0, int(shared_state.end_timestamp - time.time()))
        mins, secs = divmod(remain, 60)
        st.metric("Thời gian còn lại của Server", f"{mins:02d}:{secs:02d}")

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
is_vip = user['user_id'] in ADMIN_IDS

# --- CHECK GAME ENDED ---
# Nếu hết giờ (dựa trên timestamp toàn cục) -> Đổi status thành ENDED (logic hiển thị)
current_time = time.time()
remaining_seconds = 0
if shared_state.status == "RUNNING":
    remaining_seconds = shared_state.end_timestamp - current_time
    if remaining_seconds <= 0:
        if not is_vip:
            st.error("🛑 HẾT GIỜ! GAME ĐÃ KẾT THÚC.")
            st.stop()
        else:
             st.warning("⚠️ Admin Mode: Đã hết giờ thực tế.")

# Nếu admin bấm STOP -> User bị đá ra
if not is_vip and shared_state.status != "RUNNING":
    st.error("🛑 ADMIN ĐÃ ĐÓNG CỔNG.")
    if st.button("Thoát"):
        st.session_state.user_info = None
        st.rerun()
    st.stop()

target_gender = get_gender(user['santa_name'])
st.title("🎁 PHÒNG THẨM VẤN")

# --- REAL-TIME USER COUNTDOWN (JS) ---
# Truyền timestamp kết thúc xuống JS để nó tự đếm ngược
end_ts_js = shared_state.end_timestamp
countdown_html = f"""
<div id="countdown_display" class="countdown-box" style="
    background-color: #222; color: #FF4500; padding: 15px; 
    border-radius: 10px; text-align: center; font-size: 30px; 
    font-weight: bold; border: 2px solid #FF4500; margin-bottom: 20px;
    font-family: monospace;">
    Loading...
</div>
<script>
    var endTimestamp = {end_ts_js};
    
    function updateCountdown() {{
        var now = Date.now() / 1000;
        var diff = endTimestamp - now;
        
        if (diff <= 0) {{
            document.getElementById("countdown_display").innerHTML = "🛑 HẾT GIỜ!";
            document.getElementById("countdown_display").style.color = "red";
            return;
        }}
        
        var minutes = Math.floor(diff / 60);
        var seconds = Math.floor(diff % 60);
        
        var displayStr = (minutes < 10 ? "0" + minutes : minutes) + ":" + (seconds < 10 ? "0" + seconds : seconds);
        document.getElementById("countdown_display").innerHTML = "⏳ " + displayStr;
    }}
    
    setInterval(updateCountdown, 1000);
    updateCountdown();
</script>
"""
components.html(countdown_html, height=100)

# --- METRICS CẬP NHẬT: 5 CÂU - 3 MẠNG ---
c1, c2 = st.columns(2)
c1.metric("❓ GỢI Ý CÒN LẠI", f"{max(0, MAX_QUESTIONS - st.session_state.question_count)} / {MAX_QUESTIONS}")
c2.metric("❤️ MẠNG SỐNG", f"{MAX_LIVES - st.session_state.wrong_guesses} / {MAX_LIVES}")

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

if st.session_state.game_status == "LOST":
    st.error("☠️ GAME OVER!")
    st.info(f"Đáp án: {user['santa_name']}")
    st.stop()

if st.session_state.game_status == "WON":
    st.balloons()
    st.success(f"🎉 BẠN ĐÃ THẮNG! SECRET SANTA LÀ: {user['santa_name']}")
    st.stop()

# --- INPUT & AI LOGIC ---
if prompt := st.chat_input("Đoán tên hoặc hỏi gợi ý..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        
        # SYSTEM PROMPT CẬP NHẬT 5 CÂU / 3 MẠNG
        system_instruction = f"""
        Bạn là AI Quản trò (mã NPLM). User: {user['user_name']}. Santa: {user['santa_name']} ({target_gender}, MSHS: {user['santa_id']}).
        Status: Hỏi {st.session_state.question_count}/{MAX_QUESTIONS}. Sai {st.session_state.wrong_guesses}/{MAX_LIVES}.
        
        RULES:
        1. [[WIN]]: Đoán ĐÚNG CẢ HỌ TÊN.
        2. [[WRONG]]: Đoán tên SAI.
        3. [[OK]]: Hỏi gợi ý hợp lệ. Nếu user đã hỏi {MAX_QUESTIONS} câu -> Từ chối, bắt đoán tên.
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
                # CHECK MẠNG: >= MAX_LIVES
                if st.session_state.wrong_guesses >= MAX_LIVES:
                    st.session_state.game_status = "LOST"
                    log_activity(user['user_name'], "GAME OVER")
                    action = "LOST"
                else: action = "WRONG"
            elif "[[OK]]" in full_res:
                # CHECK CÂU HỎI: < MAX_QUESTIONS
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
