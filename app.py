import streamlit as st
import streamlit.components.v1 as components # THƯ VIỆN ĐỂ CHẠY JS TIMER
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
# --- LƯU Ý: NẾU ĐÃ DEPLOY LÊN STREAMLIT CLOUD THÌ DÙNG st.secrets ---
try:
    FIXED_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    FIXED_GROQ_API_KEY = "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" 

FIXED_CSV_PATH = "res.csv"
LOG_FILE_PATH = "game_logs.csv"  
BACKGROUND_IMAGE_NAME = "background.jpg" 

# DANH SÁCH VIP (ADMIN) - NHỮNG ID NÀY SẼ RA VÀO THOẢI MÁI
ADMIN_IDS = ["250231", "250218"]

FEMALE_NAMES = [
    "Khánh An", "Bảo Hân", "Lam Ngọc", 
    "Phương Quỳnh", "Phương Nguyên", "Minh Thư"
]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

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
    """Kiểm tra xem người chơi đã có trong danh sách thua cuộc chưa"""
    if not os.path.exists(LOG_FILE_PATH):
        return False
    try:
        df = pd.read_csv(LOG_FILE_PATH)
        # Lọc ra những dòng có hành động là GAME OVER
        losers = df[df['Hành động'] == 'GAME OVER']['Người chơi'].unique()
        return user_name in losers
    except Exception:
        return False

def get_gender(name):
    for female in FEMALE_NAMES:
        if female.lower() in name.lower(): return "Nữ"
    return "Nam"

def load_data(filepath):
    try:
        if not os.path.exists(filepath):
            return []    
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
    page_bg_img = '''
    <style>
    .stApp { background-image: linear-gradient(to bottom, #0f2027, #203a43, #2c5364); }
    </style>
    '''

st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("""
<style>
    /* KHUNG CHỨA CHÍNH */
    .main .block-container {
        background-color: rgba(0, 0, 0, 0.85) !important;
        padding: 30px !important;
        border-radius: 25px;
        border: 2px solid #FFD700;
        box-shadow: 0 0 20px rgba(0,0,0,0.8);
        max-width: 800px;
    }

    /* TYPOGRAPHY */
    h1 { 
        color: #FFD700 !important;
        text-shadow: 2px 2px 4px #000000; 
        font-family: 'Arial Black', sans-serif;
        text-align: center;
    }
    h2, h3 { color: #FFFFFF !important; text-shadow: 1px 1px 2px #000; }
    p, label, span { color: #FFFFFF !important; font-weight: 500; }

    /* CHAT BUBBLES */
    div[data-testid="user-message"] {
        background-color: #FFFFFF !important;
        color: #004d00 !important;
        border: 3px solid #2e7d32 !important;
        border-radius: 15px 15px 0px 15px !important;
        padding: 15px !important;
        font-weight: bold;
    }

    div[data-testid="assistant-message"] {
        background-color: #FFFFFF !important;
        color: #8b0000 !important;
        border: 3px solid #d32f2f !important;
        border-radius: 15px 15px 15px 0px !important;
        padding: 15px !important;
        font-weight: bold;
    }

    /* METRICS */
    div[data-testid="stMetric"] {
        background-color: #222222 !important;
        border: 1px solid #FFD700;
        border-radius: 10px;
        padding: 10px;
    }
    div[data-testid="stMetricValue"] { color: #FFD700 !important; }
    div[data-testid="stMetricLabel"] { color: #FFFFFF !important; }

    /* INPUT FIELD */
    .stTextInput input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FFD700 !important;
        font-weight: bold !important;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p { color: #FFD700 !important; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. KHỞI TẠO STATE
# ==============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "question_count" not in st.session_state:
    st.session_state.question_count = 0 
if "wrong_guesses" not in st.session_state:
    st.session_state.wrong_guesses = 0  
if "game_status" not in st.session_state:
    st.session_state.game_status = "PLAYING"
if "start_time" not in st.session_state:
    st.session_state.start_time = None

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
            
            # ĐÃ XÓA LOGIN BẰNG ID "admin" TẠI ĐÂY

            # User Login Check
            matches = [p for p in profiles if query.lower() in p['search_key'] or query in p['user_id']]
            
            if len(matches) == 1:
                selected_user = matches[0]
                
                # --- CHECK QUYỀN TRUY CẬP ---
                is_vip = selected_user['user_id'] in ADMIN_IDS # Admin được miễn tử
                has_lost = check_if_lost(selected_user['user_name'])
                
                # Nếu không phải VIP mà đã thua -> Chặn
                if not is_vip and has_lost:
                    st.error(f"🚫 {selected_user['user_name']} ơi, bạn đã dùng hết mạng và thua cuộc rồi! Không thể đăng nhập lại.")
                else:
                    st.session_state.user_info = selected_user
                    
                    # Reset game (Nếu là Admin, reset luôn để test lại từ đầu)
                    st.session_state.question_count = 0
                    st.session_state.wrong_guesses = 0
                    st.session_state.game_status = "PLAYING"
                    st.session_state.messages = []
                    st.session_state.start_time = time.time()
                    
                    # Chỉ log login nếu chưa thua (để tránh spam log admin)
                    if not has_lost:
                        log_activity(selected_user['user_name'], "Login")
                    
                    # Tin nhắn chào mừng
                    welcome_msg = f"Ho Ho Ho! Chào **{selected_user['user_name']}**! 🎅\nTa đang giữ bí mật về người tặng quà cho con.\n\nLuật chơi: Con có **3 câu hỏi** và **2 mạng**.\nLưu ý: Phải đoán đúng **HỌ VÀ TÊN** mới thắng nhé!"
                    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                    st.rerun()

            elif len(matches) > 1:
                st.warning("⚠️ Có nhiều người trùng tên, vui lòng nhập MSHS.")
            else:
                st.error("❌ Không tìm thấy tên trong danh sách.")
    st.stop()

# ==============================================================================
# 6. MÀN HÌNH ADMIN (TIMER + COUNTDOWN)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ TRUNG TÂM CHỈ HUY (ADMIN)")
    
    # Tính tổng số giây đã trôi qua kể từ khi server chạy (Python)
    initial_uptime_seconds = (datetime.datetime.now() - SERVER_START_TIME).total_seconds()
    
    # ----------------------------------------------------
    # JS: UPTIME CLOCK + 5 MINS COUNTDOWN
    # ----------------------------------------------------
    dashboard_html = f"""
    <div style="display: flex; gap: 20px; justify-content: center;">
        <div style="
            flex: 1;
            padding: 15px;
            border: 2px solid #FFD700;
            border-radius: 10px;
            background-color: #222222;
            color: #FFD700;
            font-family: 'Arial', sans-serif;
            text-align: center;
        ">
            <div style="font-size: 14px; color: #aaa;">SERVER UPTIME</div>
            <div id="uptime_clock" style="font-size: 28px; font-weight: bold;">Loading...</div>
        </div>

        <div style="
            flex: 1;
            padding: 15px;
            border: 2px solid #FF4500;
            border-radius: 10px;
            background-color: #222222;
            color: #FF4500;
            font-family: 'Arial', sans-serif;
            text-align: center;
        ">
            <div style="font-size: 14px; color: #aaa;">COUNTDOWN (5 MINS)</div>
            <div id="countdown_clock" style="font-size: 28px; font-weight: bold;">05:00</div>
            <div style="margin-top: 5px;">
                <button onclick="startCountdown()" style="cursor:pointer; background:#FF4500; color:white; border:none; border-radius:3px; padding:2px 8px;">Start</button>
                <button onclick="resetCountdown()" style="cursor:pointer; background:#555; color:white; border:none; border-radius:3px; padding:2px 8px;">Reset</button>
            </div>
        </div>
    </div>

    <script>
        // --- LOGIC UPTIME ---
        let uptime = {initial_uptime_seconds};
        function formatTime(s) {{
            let h = Math.floor(s / 3600);
            let m = Math.floor((s % 3600) / 60);
            let sc = Math.floor(s % 60);
            return (h < 10 ? "0"+h : h) + ":" + (m < 10 ? "0"+m : m) + ":" + (sc < 10 ? "0"+sc : sc);
        }}
        setInterval(() => {{
            uptime += 1;
            document.getElementById("uptime_clock").innerText = formatTime(uptime);
        }}, 1000);

        // --- LOGIC COUNTDOWN ---
        let countdownTime = 300; // 5 minutes
        let countdownInterval = null;
        
        function updateCountdownDisplay() {{
            let m = Math.floor(countdownTime / 60);
            let s = countdownTime % 60;
            document.getElementById("countdown_clock").innerText = 
                (m < 10 ? "0"+m : m) + ":" + (s < 10 ? "0"+s : s);
        }}

        function startCountdown() {{
            if (countdownInterval) return; // Prevent multiple clicks
            countdownInterval = setInterval(() => {{
                if (countdownTime > 0) {{
                    countdownTime--;
                    updateCountdownDisplay();
                }} else {{
                    clearInterval(countdownInterval);
                    document.getElementById("countdown_clock").innerText = "HẾT GIỜ!";
                }}
            }}, 1000);
        }}

        function resetCountdown() {{
            clearInterval(countdownInterval);
            countdownInterval = null;
            countdownTime = 300;
            updateCountdownDisplay();
        }}
    </script>
    """
    components.html(dashboard_html, height=150)
    # ----------------------------------------------------

    if st.session_state.user_info:
        if st.button("⬅️ QUAY LẠI GAME", type="primary"):
            st.session_state.is_admin = False
            st.rerun()
    else:
        # Trường hợp này khó xảy ra vì đã bỏ login admin, nhưng cứ để
        if st.button("⬅️ THOÁT ADMIN", type="secondary"):
            st.session_state.is_admin = False
            st.rerun()

    if os.path.exists(LOG_FILE_PATH):
        df_log = pd.read_csv(LOG_FILE_PATH)
        if 'Hành động' in df_log.columns and 'Người chơi' in df_log.columns:
            df_win = df_log[df_log['Hành động'] == 'WIN']
            list_winners = df_win['Người chơi'].unique()
            df_loss = df_log[df_log['Hành động'] == 'GAME OVER']
            list_losers = df_loss['Người chơi'].unique()
            
            col1, col2 = st.columns(2)
            col1.metric("🏆 ĐÃ THẮNG", len(list_winners))
            col2.metric("💀 ĐÃ THUA", len(list_losers))
            
            st.write("")
            if st.button("🗑️ XÓA DỮ LIỆU LOG", type="secondary"):
                 os.remove(LOG_FILE_PATH)
                 st.rerun()
                 
            st.write("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🏆 Winner List")
                if len(list_winners)>0: st.dataframe(list_winners, use_container_width=True)
            with c2:
                st.markdown("### 💀 Loser List (Blocked)")
                if len(list_losers)>0: st.dataframe(list_losers, use_container_width=True)
                
            with st.expander("Show Full Logs"):
                st.dataframe(df_log.sort_values(by="Thời gian", ascending=False), use_container_width=True)
        else:
            st.warning("File log bị lỗi định dạng.")
    else:
        st.warning("Chưa có log.")
    st.stop()

# ==============================================================================
# 7. MÀN HÌNH GAME CHÍNH
# ==============================================================================
user = st.session_state.user_info
target_gender = get_gender(user['santa_name'])

st.title("🎁PHÒNG THẨM VẤN ÔNG GIÀ NOEL")

# --- Xử lý Timer cho User (Chỉ update khi tương tác) ---
elapsed_str = "00:00"
if st.session_state.start_time:
    elapsed = int(time.time() - st.session_state.start_time)
    mins, secs = divmod(elapsed, 60)
    elapsed_str = f"{mins:02d}:{secs:02d}"

# --- Metrics Bar ---
c1, c2, c3 = st.columns(3)
c1.metric("❓ GỢI Ý", f"{max(0, 3 - st.session_state.question_count)} / 3")
c2.metric("❤️ MẠNG", f"{2 - st.session_state.wrong_guesses}")
c3.metric("⏳ THỜI GIAN", elapsed_str)

# --- Sidebar ---
with st.sidebar:
    st.title(f"👤 {user['user_name']}")
    st.caption(f"ID: {user['user_id']}")
    st.caption(f"Trạng thái: {st.session_state.game_status}")
    st.divider()
    
    # Nút vào Admin chỉ hiện nếu User ID nằm trong danh sách VIP
    if user['user_id'] in ADMIN_IDS:
        if st.button("🛡️ VÀO ADMIN", type="primary"):
            st.session_state.is_admin = True
            st.rerun()
            
    if st.button("Đăng xuất"):
         st.session_state.user_info = None
         st.session_state.messages = []
         st.session_state.start_time = None
         st.rerun()

# --- Hiển thị Chat ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Kiểm tra trạng thái kết thúc ---
if st.session_state.game_status == "LOST":
    st.error("☠️ GAME OVER! HẾT QUÀ RỒI! ☠️")
    st.info(f"Đáp án đúng là: {user['santa_name']}")
    st.stop()

if st.session_state.game_status == "WON":
    st.balloons()
    st.snow()
    st.success(f"🎉 CHÚC MỪNG! SECRET SANTA LÀ: {user['santa_name']} 🎉")
    st.stop()

# --- Xử lý Input & Logic AI ---
if prompt := st.chat_input("Đoán tên (Cần cả Họ Tên) hoặc hỏi gợi ý..."):
    
    # User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        client = Groq(api_key=FIXED_GROQ_API_KEY)
        
        # LOGIC PROMPT CHO AI
        system_instruction = f"""
        Bạn là AI Quản trò Secret Santa (tên mã NPLM). Tính cách: Lạnh lùng, hơi châm biếm, nhưng công bằng.
        
        DỮ LIỆU BÍ MẬT:
        - Người chơi (User): {user['user_name']}
        - Kẻ Bí Mật (Santa): {user['santa_name']} (Giới tính: {target_gender}, MSHS: {user['santa_id']})
        - Trạng thái: Đã hỏi {st.session_state.question_count}/3. Sai {st.session_state.wrong_guesses}/2.
        
        QUY TẮC TUYỆT ĐỐI - BẠN PHẢI BẮT ĐẦU CÂU TRẢ LỜI BẰNG MỘT TRONG CÁC TOKEN SAU:

        1. [[WIN]] : Nếu user đoán ĐÚNG CẢ HỌ VÀ TÊN của Kẻ Bí Mật. (Vd: "Là Nguyễn Văn A à" -> [[WIN]]).
        2. [[WRONG]] : Nếu user cố tình đoán tên một người cụ thể nhưng SAI. (Vd: "Là Lê Thị B hả" -> [[WRONG]]).
           - Kèm lời chế giễu nhẹ nhàng.
        3. [[OK]] : Nếu user đặt câu hỏi gợi ý hợp lệ (Về giới tính, MSHS, tên đệm...).
           - Nếu đã hỏi hết 3 câu -> KHÔNG dùng [[OK]], hãy từ chối và bảo họ đoán tên đi.
           - Nếu hỏi về ngoại hình -> Từ chối (camera hỏng).
        4. [[CHAT]] : Các câu chat xã giao thông thường, không đoán tên cũng không xin gợi ý.

        Lưu ý:
        - KHÔNG tiết lộ tên thật trừ khi đã có token [[WIN]].
        - Hỗ trợ toán học về MSHS (chia hết, lớn hơn, nhỏ hơn...).
        - Gợi ý tên: Số chữ cái, chữ cái đầu.
        - Nếu user không ghi đủ họ và tên thì nhắc nhở user
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
                    # Ẩn token khi đang stream text để user không thấy
                    clean_preview = full_response.replace("[[WIN]]", "").replace("[[WRONG]]", "").replace("[[OK]]", "").replace("[[CHAT]]", "")
                    message_placeholder.markdown(clean_preview + "▌")
            
            # Xử lý Logic Game dựa trên Token AI trả về
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
                    final_content = "Ngươi đã hết câu hỏi gợi ý rồi! Giờ chỉ được đoán tên thôi (Đoán sai là mất mạng đấy!)."
            
            else:
                 final_content = full_response.replace("[[CHAT]]", "")

            # Hiển thị lại nội dung sạch
            message_placeholder.markdown(final_content)
            st.session_state.messages.append({"role": "assistant", "content": final_content})
            
            # Rerun để cập nhật giao diện (số mạng, số câu hỏi, timer)
            if status_update in ["WIN", "LOST", "WRONG", "OK"]:
                time.sleep(1)
                st.rerun()

    except Exception as e:
        st.error(f"Lỗi kết nối AI: {str(e)}")
