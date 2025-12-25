import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from groq import Groq
import os
import datetime
import csv
import time
import base64
import json  # Đã thêm thư viện json để đồng bộ Admin mới

# ==============================================================================
# 1. CẤU HÌNH & CONSTANTS
# ==============================================================================
try:
    FIXED_GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    FIXED_GROQ_API_KEY = "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"

FIXED_CSV_PATH = "res.csv"
LOG_FILE_PATH = "game_logs.csv"
CONFIG_FILE_PATH = "game_config.json" # File để Admin điều khiển game toàn server
BACKGROUND_IMAGE_NAME = "background.jpg"

# DANH SÁCH ADMIN (ID) - Bạn có thể cập nhật thêm
ADMIN_IDS = ["250231", "250218", "admin"]

# --- LUẬT CHƠI ---
MAX_QUESTIONS = 5   # 5 Câu hỏi gợi ý
MAX_LIVES = 3       # 3 Mạng
DEFAULT_DURATION = 15 # Mặc định 15 phút nếu reset file

FEMALE_NAMES = ["Khánh An", "Bảo Hân", "Lam Ngọc", "Phương Quỳnh", "Phương Nguyên", "Minh Thư"]

st.set_page_config(page_title="Secret Santa Festive", page_icon="🎄", layout="centered")

# ==============================================================================
# 2. UTILS (HÀM HỖ TRỢ)
# ==============================================================================

# --- LOGIC QUẢN LÝ TRẠNG THÁI GAME TỪ ADMIN MỚI ---
def get_game_config():
    """Đọc cấu hình game (thời gian kết thúc) từ file JSON"""
    # Nếu file chưa tồn tại, tạo mặc định là đang đóng
    if not os.path.exists(CONFIG_FILE_PATH):
        return {"end_time_epoch": 0, "is_active": False}
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"end_time_epoch": 0, "is_active": False}

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

# --- CÁC HÀM XỬ LÝ KHÁC (GIỮ NGUYÊN TỪ CODE CŨ) ---
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
# 3. CSS & GIAO DIỆN (GIỮ NGUYÊN TỪ CODE CŨ)
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
    
    /* METRIC FOR ADMIN */
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

# Lấy config hiện tại
current_config = get_game_config()
is_game_active = current_config["is_active"]
game_end_time = current_config["end_time_epoch"]
current_time = time.time()

# ==============================================================================
# 5. MÀN HÌNH ĐĂNG NHẬP (CỔNG CHÀO)
# ==============================================================================
if st.session_state.user_info is None and not st.session_state.is_admin:
    st.title("🎄 CỔNG GIÁNG SINH 🎄")
    st.markdown("<h3 style='color: #FFD700; margin-bottom: 20px;'>SECRET SANTA FESTIVE</h3>", unsafe_allow_html=True)
    
    # STATUS CHECK (Dựa trên config JSON)
    if not is_game_active:
        st.info("⏳ CỔNG CHƯA MỞ HOẶC ĐÃ BỊ ADMIN ĐÓNG.")
    elif current_time > game_end_time:
        st.error("🛑 SỰ KIỆN ĐÃ KẾT THÚC (HẾT GIỜ).")
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
                
                # Logic Gatekeeper (Cập nhật theo config JSON)
                allow_entry = True
                if not is_admin_user:
                    if not is_game_active or current_time > game_end_time:
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
                    if not is_game_active: st.warning("🚧 Cổng chưa mở.")
                    else: st.error("🏁 Đã hết giờ.")
            elif len(matches) > 1: st.warning("⚠️ Trùng tên, vui lòng nhập MSHS.")
            else: st.error("❌ Không tìm thấy dữ liệu.")
    st.stop()

# ==============================================================================
# 6. ADMIN PANEL (THAY MỚI THEO YÊU CẦU)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛡️ CONTROL CENTER (ADMIN)")
    
    # --- PANEL ĐIỀU KHIỂN THỜI GIAN ---
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
    is_active_js = str(config["is_active"]).lower()

    # JS Countdown hiển thị cho Admin xem chơi
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

    # --- LOGS VÀ THỐNG KÊ ---
    st.markdown("### 📊 THỐNG KÊ REAL-TIME")
    if os.path.exists(LOG_FILE_PATH):
        df_log = pd.read_csv(LOG_FILE_PATH)
        # Đảm bảo có cột cần thiết
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
    
    st.stop()

# ==============================================================================
# 7. MAIN GAME INTERFACE (CĂN GIỮA DASHBOARD)
# ==============================================================================
user = st.session_state.user_info
is_vip = user['user_id'] in ADMIN_IDS

# Cập nhật trạng thái mới nhất từ file Config
config = get_game_config()
is_active = config["is_active"]
end_timestamp = config["end_time_epoch"]

# Check Timeout
if is_active:
    if time.time() > end_timestamp:
        if not is_vip:
            st.error("🛑 HẾT GIỜ! GAME OVER.")
            st.stop()
        else: st.toast("Admin Mode: Time is up.")

if not is_vip and not is_active:
    st.error("🛑 KẾT NỐI BỊ NGẮT (ADMIN STOP).")
    if st.button("Thoát"):
        st.session_state.user_info = None
        st.rerun()
    st.stop()

target_gender = get_gender(user['santa_name'])

st.title("🎁 PHÒNG THẨM VẤN")

# --- CUSTOM DASHBOARD (HTML/CSS/JS) ---
q_left = max(0, MAX_QUESTIONS - st.session_state.question_count)
l_left = MAX_LIVES - st.session_state.wrong_guesses
# Truyền biến xuống JS
end_ts_js = end_timestamp if is_active else 0

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
        Bạn là AI Quản trò Secret Santa (tên mã NPLM). Tính cách: Lạnh lùng, bí hiểm, thích đánh đố, châm biếm nhưng công bằng.
        
        DỮ LIỆU BÍ MẬT:
        - Người chơi (User): {user['user_name']}
        - Kẻ Bí Mật (Santa): {user['santa_name']} (Giới tính: {target_gender}, MSHS: {user['santa_id']})
        - Trạng thái: Đã hỏi {st.session_state.question_count}/{MAX_QUESTIONS}. Sai {st.session_state.wrong_guesses}/{MAX_LIVES}.
        
        CẤU TRÚC TÊN SANTA (Quan trọng):
        - Tên Santa có dạng: [Họ] [Đệm] [Tên].
        - Ví dụ: "Phạm Lê Minh Quân" -> Họ: Phạm, Đệm: Lê Minh, Tên chính: Quân.
        - Mọi gợi ý về "Tên" chỉ liên quan đến "Tên chính" (từ cuối cùng).
        - Gợi ý về "Họ" là từ đầu tiên.
        - Gợi ý về "Chữ lót/Đệm" là các từ ở giữa.

        QUY TẮC TUYỆT ĐỐI - BẠN PHẢI BẮT ĐẦU CÂU TRẢ LỜI BẰNG MỘT TRONG CÁC TOKEN SAU:

        1. [[WIN]] : 
           - Chỉ dùng khi user đoán ĐÚNG CẢ HỌ VÀ TÊN của Kẻ Bí Mật (chấp nhận không dấu, viết thường, đủ các thành phần). 
           - Ví dụ: Santa là "Nguyễn Văn A". User đoán "Nguyễn Văn A" -> [[WIN]].
           - Nếu thiếu họ hoặc đệm -> Dùng [[CHAT]] để nhắc nhở ghi đầy đủ.

        2. [[WRONG]] : 
           - Dùng khi user cố tình đưa ra một cái tên cụ thể (có vẻ là Họ Tên) để đoán nhưng SAI.
           - Kèm lời chế giễu nhẹ nhàng về sự tự tin thái quá của họ.

        3. [[OK]] : 
           - Dùng khi user đặt câu hỏi gợi ý hợp lệ (Về giới tính, MSHS, tên chính, họ, chữ lót...).
           - Nếu đã hỏi hết {MAX_QUESTIONS} câu -> KHÔNG dùng [[OK]]. Hãy từ chối lạnh lùng và ép họ đoán tên.
           - Nếu hỏi về ngoại hình/khuôn mặt -> Từ chối (bảo camera hỏng hoặc ta không quan tâm vẻ bề ngoài).
           - Khi hỏi về "Tên": Chỉ gợi ý về TÊN CHÍNH (từ cuối cùng), ví dụ số chữ cái, chữ cái đầu của tên chính.

        4. [[CHAT]] : 
           - Các câu chat xã giao, tào lao, không đoán tên cũng không xin gợi ý.
           - Dùng để nhắc nhở nếu user đoán tên mà thiếu họ/đệm.
           - Xử lý câu hỏi về MSHS: TUYỆT ĐỐI KHÔNG tiết lộ con số cụ thể. Chỉ dùng các phép so sánh toán học (lớn hơn, bé hơn, chia hết cho X, là số nguyên tố hay không...). So sánh MSHS của Santa với MSHS của User ({user['user_id']}) là một cách hay.

        LƯU Ý QUAN TRỌNG KHI TRẢ LỜI:
        - KHÔNG BAO GIỜ tiết lộ tên thật hoặc MSHS cụ thể của Santa trừ khi đã [[WIN]].
        - Mục tiêu: Làm cho trò chơi KHÓ NHẤT CÓ THỂ. Đừng gợi ý quá rõ ràng. Hãy dùng câu đố hoặc ẩn dụ.
        - Hãy trả lời dài dòng, văn vở, bí hiểm một chút.
        - Sử dụng nhiều emoji 🎄🎅❄️🎁💀😈 phù hợp với tính cách quản trò bí ẩn.
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






