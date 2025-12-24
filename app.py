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

# DANH SÁCH VIP (ADMIN) - BẤT TỬ, RA VÀO TỰ DO
ADMIN_IDS = ["250231", "250218", "admin"] # Thêm 'admin' để test cho dễ

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# --- QUẢN LÝ TRẠNG THÁI GAME TOÀN SERVER (QUAN TRỌNG) ---
class SharedGameState:
    def __init__(self):
        # status: "WAITING", "RUNNING", "ENDED"
        self.status = "WAITING" 

@st.cache_resource
def get_shared_state():
    return SharedGameState()

shared_state = get_shared_state()

# ==============================================================================
# 2. UTILS & HÀM HỖ TRỢ
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
    h1 { color: #FFD700 !important; text-shadow: 2px 2px 4px #000; font-family: 'Arial Black', sans-serif; text-align: center; }
    h2, h3, p, label, span { color: #FFFFFF !important; }
    div[data-testid="user-message"] { background-color: #FFFFFF !important; color: #004d00 !important; border-radius: 15px 15px 0px 15px !important; padding: 15px !important; font-weight: bold; }
    div[data-testid="assistant-message"] { background-color: #FFFFFF !important; color: #8b0000 !important; border-radius: 15px 15px 15px 0px !important; padding: 15px !important; font-weight: bold; }
    div[data-testid="stMetric"] { background-color: #222222 !important; border: 1px solid #FFD700; border-radius: 10px; }
    div[data-testid="stMetricValue"] { color: #FFD700 !important; }
    .stTextInput input { background-color: #FFFFFF !important; color: #000000 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p { color: #FFD700 !important; }
    #MainMenu, footer, header {visibility: hidden;}
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
if "start_time" not in st.session_state: st.session_state.start_time = None

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    st.title("🎅 CỔNG ĐĂNG NHẬP")
    
    # --- HIỂN THỊ TRẠNG THÁI SERVER ---
    if shared_state.status == "WAITING":
        st.info("⏳ TRÒ CHƠI CHƯA BẮT ĐẦU. VUI LÒNG CHỜ HIỆU LỆNH TỪ ADMIN.")
    elif shared_state.status == "ENDED":
        st.error("🛑 TRÒ CHƠI ĐÃ KẾT THÚC.")
    else:
        st.success("🟢 TRÒ CHƠI ĐANG DIỄN RA! VÀO NGAY!")

    profiles = load_data(FIXED_CSV_PATH)

    with st.form("login_form"):
        st.markdown("**Nhập thông tin của bạn:**")
        user_input = st.text_input("Mã số học sinh (hoặc Tên):", placeholder="Ví dụ: 250231...")
        submitted = st.form_submit_button("🚀 BẮT ĐẦU CHƠI NGAY", type="primary")

        if submitted and user_input:
            query = user_input.strip()
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                is_admin_user = selected_user['user_id'] in ADMIN_IDS
                
                # --- LOGIC KIỂM SOÁT RA VÀO ---
                # 1. Nếu là Admin: Vào luôn, không quan tâm trạng thái game
                # 2. Nếu là User thường: Phải check trạng thái game
                
                allow_entry = False
                
                if is_admin_user:
                    allow_entry = True
                else:
                    if shared_state.status == "WAITING":
                        st.warning("🚧 Admin chưa mở cổng trò chơi. Vui lòng quay lại sau.")
                    elif shared_state.status == "ENDED":
                        st.error("🏁 Trò chơi đã kết thúc. Hẹn gặp lại mùa sau!")
                    else:
                        allow_entry = True

                if allow_entry:
                    has_lost = check_if_lost(selected_user['user_name'])
                    if not is_admin_user and has_lost:
                        st.error(f"🚫 {selected_user['user_name']} ơi, bạn đã thua rồi! Không thể đăng nhập lại.")
                    else:
                        st.session_state.user_info = selected_user
                        st.session_state.question_count = 0
                        st.session_state.wrong_guesses = 0
                        st.session_state.game_status = "PLAYING"
                        st.session_state.messages = []
                        st.session_state.start_time = time.time()
                        
                        if not has_lost: log_activity(selected_user['user_name'], "Login")
                        
                        welcome_msg = f"Ho Ho Ho! Chào **{selected_user['user_name']}**! 🎅\n\n- Con có **3 câu hỏi** và **2 mạng**.\n- Đoán đúng **HỌ VÀ TÊN** để thắng.\n- Chúc may mắn!"
                        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                        st.rerun()

            elif len(matches) > 1:
                st.warning("⚠️ Có nhiều người trùng tên, vui lòng nhập MSHS.")
            else:
                st.error("❌ Không tìm thấy tên trong danh sách.")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH ADMIN (CONTROL PANEL)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ TRUNG TÂM CHỈ HUY (ADMIN)")
    
    # --- ĐIỀU KHIỂN TRẠNG THÁI GAME ---
    st.markdown("### 🕹️ ĐIỀU KHIỂN SERVER")
    
    status_color = "orange" if shared_state.status == "WAITING" else ("green" if shared_state.status == "RUNNING" else "red")
    st.markdown(f"TRẠNG THÁI HIỆN TẠI: **:{status_color}[{shared_state.status}]**")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶️ MỞ CỔNG TRÒ CHƠI (START)", type="primary", use_container_width=True):
            shared_state.status = "RUNNING"
            st.rerun()
    with col_b:
        if st.button("🛑 ĐÓNG CỔNG TRÒ CHƠI (END)", type="primary", use_container_width=True):
            shared_state.status = "ENDED"
            st.rerun()
            
    st.divider()

    initial_uptime_seconds = (datetime.datetime.now() - SERVER_START_TIME).total_seconds()
    
    # DASHBOARD HTML (Giữ nguyên countdown của bạn)
    dashboard_html = f"""
    <div style="display: flex; gap: 20px; justify-content: center;">
        <div style="flex: 1; padding: 15px; border: 2px solid #FFD700; border-radius: 10px; background-color: #222; color: #FFD700; text-align: center;">
            <div style="font-size: 14px; color: #aaa;">SERVER UPTIME</div>
            <div id="uptime_clock" style="font-size: 28px; font-weight: bold;">Loading...</div>
        </div>
        <div style="flex: 1; padding: 15px; border: 2px solid #FF4500; border-radius: 10px; background-color: #222; color: #FF4500; text-align: center;">
            <div style="font-size: 14px; color: #aaa;">COUNTDOWN (5 MINS)</div>
            <div id="countdown_clock" style="font-size: 28px; font-weight: bold;">05:00</div>
            <div style="margin-top: 5px;">
                <button onclick="startCountdown()" style="cursor:pointer; background:#FF4500; color:white; border:none; border-radius:3px; padding:2px 8px;">Start</button>
                <button onclick="resetCountdown()" style="cursor:pointer; background:#555; color:white; border:none; border-radius:3px; padding:2px 8px;">Reset</button>
            </div>
        </div>
    </div>
    <script>
        let uptime = {initial_uptime_seconds};
        function formatTime(s) {{ let h=Math.floor(s/3600); let m=Math.floor((s%3600)/60); let sc=Math.floor(s%60); return (h<10?"0"+h:h)+":"+(m<10?"0"+m:m)+":"+(sc<10?"0"+sc:sc); }}
        setInterval(()=>{{ uptime+=1; document.getElementById("uptime_clock").innerText=formatTime(uptime); }}, 1000);
        
        let countdownTime=300; let countdownInterval=null;
        function updateDisplay(){{ let m=Math.floor(countdownTime/60); let s=countdownTime%60; document.getElementById("countdown_clock").innerText=(m<10?"0"+m:m)+":"+(s<10?"0"+s:s); }}
        function startCountdown(){{ if(countdownInterval)return; countdownInterval=setInterval(()=>{{ if(countdownTime>0){{countdownTime--;updateDisplay();}}else{{clearInterval(countdownInterval);document.getElementById("countdown_clock").innerText="HẾT GIỜ!";}} }},1000); }}
        function resetCountdown(){{ clearInterval(countdownInterval); countdownInterval=null; countdownTime=300; updateDisplay(); }}
    </script>
    """
    components.html(dashboard_html, height=150)

    if st.button("⬅️ QUAY LẠI GAME (ADMIN MODE)"):
        st.session_state.is_admin = False
        st.rerun()

    # --- LOG VIEWING ---
    if os.path.exists(LOG_FILE_PATH):
        df_log = pd.read_csv(LOG_FILE_PATH)
        if 'Hành động' in df_log.columns:
            st.write("---")
            col1, col2 = st.columns(2)
            col1.metric("🏆 WINNERS", len(df_log[df_log['Hành động']=='WIN']['Người chơi'].unique()))
            col2.metric("💀 LOSERS", len(df_log[df_log['Hành động']=='GAME OVER']['Người chơi'].unique()))
            
            with st.expander("Xem chi tiết Logs"):
                st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
            
            if st.button("🗑️ XÓA LOGS", type="secondary"):
                 os.remove(LOG_FILE_PATH)
                 st.rerun()
    st.stop()

# ==============================================================================
# 7. MÀN HÌNH GAME CHÍNH (USER)
# ==============================================================================
user = st.session_state.user_info

# --- BẢO VỆ LAYER 2: NẾU GAME ĐANG CHƠI MÀ ADMIN BẤM DỪNG ĐỘT NGỘT ---
# Nếu không phải Admin và Trạng thái game != RUNNING -> Đá văng ra ngoài
is_vip = user['user_id'] in ADMIN_IDS
if not is_vip and shared_state.status != "RUNNING":
    st.error("🛑 ADMIN ĐÃ ĐÓNG CỔNG TRÒ CHƠI HOẶC TRÒ CHƠI CHƯA BẮT ĐẦU.")
    if st.button("Quay về màn hình chính"):
        st.session_state.user_info = None
        st.rerun()
    st.stop()

target_gender = get_gender(user['santa_name'])
st.title("🎁 PHÒNG THẨM VẤN")

elapsed_str = "00:00"
if st.session_state.start_time:
    elapsed = int(time.time() - st.session_state.start_time)
    mins, secs = divmod(elapsed, 60)
    elapsed_str = f"{mins:02d}:{secs:02d}"

c1, c2, c3 = st.columns(3)
c1.metric("❓ GỢI Ý", f"{max(0, 3 - st.session_state.question_count)} / 3")
c2.metric("❤️ MẠNG", f"{2 - st.session_state.wrong_guesses}")
c3.metric("⏳ THỜI GIAN", elapsed_str)

with st.sidebar:
    st.title(f"👤 {user['user_name']}")
    
    # Chỉ Admin mới thấy nút này
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

if prompt := st.chat_input("Đoán tên (Cần cả Họ Tên) hoặc hỏi gợi ý..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        system_instruction = f"""
        Bạn là AI Quản trò (mã NPLM). User: {user['user_name']}. Santa: {user['santa_name']} ({target_gender}, MSHS: {user['santa_id']}).
        Status: Hỏi {st.session_state.question_count}/3. Sai {st.session_state.wrong_guesses}/2.
        
        RULES:
        1. [[WIN]]: Nếu đoán ĐÚNG CẢ HỌ TÊN Santa.
        2. [[WRONG]]: Nếu đoán tên cụ thể mà SAI.
        3. [[OK]]: Nếu hỏi gợi ý hợp lệ (MSHS, giới tính...). Nếu hết lượt gợi ý -> Từ chối.
        4. [[CHAT]]: Chat xã giao.
        
        Không tiết lộ tên thật trừ khi [[WIN]].
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
                if st.session_state.wrong_guesses >= 2:
                    st.session_state.game_status = "LOST"
                    log_activity(user['user_name'], "GAME OVER")
                    action = "LOST"
                else: action = "WRONG"
            elif "[[OK]]" in full_res:
                if st.session_state.question_count < 3:
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
