import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import google.generativeai as genai
import json
import re

# --- 1. CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide", page_icon="🛡️")

# CSS tạo kiểu nút bấm nổi bật, thẻ màu và giao diện chỉ huy
st.markdown("""
<style>
    /* Nút lưu phương án to, viền nổi và màu nổi bật */
    div.stButton > button[kind="primary"] {
        font-size: 18px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        background: linear-gradient(90deg, #1e7e34, #28a745) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(40, 167, 69, 0.35) !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(40, 167, 69, 0.5) !important;
        background: linear-gradient(90deg, #19692c, #218838) !important;
    }
    .custom-save-btn {
        margin-top: 15px;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

def get_gemini_key():
    if "GEMINI_API_KEY" in st.secrets:
        return str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
    for sec_name in st.secrets:
        sec = st.secrets[sec_name]
        if isinstance(sec, dict) and "GEMINI_API_KEY" in sec:
            return str(sec["GEMINI_API_KEY"]).strip().strip('"').strip("'")
    for k, v in st.secrets.items():
        if isinstance(v, str) and v.strip().startswith("AIza"):
            return v.strip().strip('"').strip("'")
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, str) and sub_v.strip().startswith("AIza"):
                    return sub_v.strip().strip('"').strip("'")
    return ""

try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
    GEMINI_API_KEY = get_gemini_key()
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Kiểm tra lại Streamlit Secrets!")
    st.stop()

# Danh sách nữ đồng chí miễn gác đêm / tuần tra đêm
LIST_NU = [
    "Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương",
    "Huỳnh Thụy Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm", "Lê Thanh Tuyền"
]

# Danh mục các điểm trực cố định theo 3 file kế hoạch
DANH_SACH_CHOT = ["Ngã ba Cây Trắc", "Cổng KCN", "Trung Tâm hành chính"]
DANH_SACH_TRUONG = [
    "TH Tân Thành Phân Hiệu 1", "Mầm non Hoa Phong Lan", "THCS Tân Thành",
    "TH Tân Thành", "Mầm non Sơn Ca", "THCS Tân Thành Phân Hiệu", "THPT Lê Lợi"
]

# --- 2. HÀM DÒ TÌM MODEL GEMINI ---
def get_working_gemini_model():
    candidate_models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    for model_name in candidate_models:
        try:
            return genai.GenerativeModel(model_name)
        except Exception:
            continue
    return genai.GenerativeModel("gemini-1.5-flash")

# --- 3. LOAD VÀ CACHE DỮ LIỆU ---
@st.cache_data(ttl=60, show_spinner=False)
def load_data(_conn, sheet_url, worksheet):
    return _conn.read(spreadsheet=sheet_url, worksheet=worksheet)

conn = st.connection("gsheets", type=GSheetsConnection)
df_raw = load_data(conn, URL_SHEET, "luutru")
df_raw = df_raw.iloc[2:].copy()

cols = ["Tuan", "Ap", "HoTen"]
day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

for code in day_codes:
    cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
df_raw.columns = cols[:len(df_raw.columns)]
df_mem = df_raw.dropna(subset=['HoTen']).copy()
dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

if "df_history" not in st.session_state:
    df_h = load_data(conn, URL_SHEET, "NhiemVu")
    if df_h.empty:
        df_h = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao", "NgayThucTe"])
    elif "NgayThucTe" not in df_h.columns:
        df_h["NgayThucTe"] = ""
    st.session_state["df_history"] = df_h
df_history = st.session_state["df_history"]

# --- 4. TÍNH TOÁN NGÀY THỰC TẾ & NHẬN DIỆN TUẦN ---
def parse_week_start(week_str):
    today = date.today()
    match = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", str(week_str))
    if match:
        d1, m1 = int(match.group(1)), int(match.group(2))
        return date(today.year, m1, d1)
    return None

list_tuan = df_mem['Tuan'].dropna().unique().tolist()[::-1]
today = date.today()
current_week_idx = 0
next_week_idx = 0

for i, w in enumerate(list_tuan):
    st_date = parse_week_start(w)
    if st_date:
        if st_date <= today <= st_date + timedelta(days=6):
            current_week_idx = i
            next_week_idx = max(0, i - 1)
            break

# --- 5. SIDEBAR ---
st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
access_key = st.sidebar.text_input("Mã điều hành:", type="password")
is_admin = (access_key == ADMIN_PASSWORD)

default_choice_idx = next_week_idx if today.weekday() >= 1 and next_week_idx != current_week_idx else current_week_idx
selected_week = st.sidebar.selectbox("Tuần làm việc:", list_tuan, index=default_choice_idx)
week_start_date = parse_week_start(selected_week)

day_options = []
day_to_actual_date = {}
for i, d_name in enumerate(days_vn):
    if week_start_date:
        act_d = week_start_date + timedelta(days=i)
        label = f"{d_name} ({act_d.strftime('%d/%m/%Y')})"
        day_to_actual_date[label] = act_d.strftime('%Y-%m-%d')
    else:
        label = d_name
        day_to_actual_date[label] = today.strftime('%Y-%m-%d')
    day_options.append(label)

cur_weekday = datetime.now().weekday()
selected_day_label = st.sidebar.selectbox("Ngày chi tiết:", day_options, index=0 if selected_week != list_tuan[current_week_idx] else cur_weekday)
selected_day = selected_day_label.split(" (")[0]
actual_date_str = day_to_actual_date[selected_day_label]

st.sidebar.divider()
st.sidebar.subheader("⏰ Ca gác cổng trụ sở")
default_times = "07-10h, 10-13h, 13-15h, 15-17h, 17-20h, 20-23h, 23-01h, 01-03h, 03-05h, 05-07h"
custom_times_str = st.sidebar.text_area("Giờ gác cổng:", value=default_times)
list_gio = [t.strip() for t in custom_times_str.split(",") if t.strip()]

# Dữ liệu quân số của tuần đang chọn
d_code = dict(zip(days_vn, day_codes))[selected_day]
df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

# --- 6. THUẬT TOÁN XOAY ĐỀU QUÂN CẢ TUẦN ---
def generate_balanced_week_schedule(week_str, df_week_pool):
    member_load = {name: 0 for name in df_week_pool['HoTen'].unique()}
    week_tasks = []

    for day_idx, d_vn in enumerate(days_vn):
        c_code = day_codes[day_idx]
        act_date = (week_start_date + timedelta(days=day_idx)).strftime('%Y-%m-%d') if week_start_date else datetime.now().strftime('%Y-%m-%d')

        day_morning = df_week_pool[df_week_pool[f"{c_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        day_night_cax = df_week_pool[df_week_pool[f"{c_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

        day_morning_nam = [n for n in day_morning if n not in LIST_NU]
        day_night_nam = [n for n in day_night_cax if n not in LIST_NU]

        used_in_day = set()

        def select_best(candidates, allow_reuse=False):
            pool = [c for c in candidates if c not in used_in_day]
            if not pool and allow_reuse:
                pool = candidates
            if not pool:
                return "Chưa đủ quân số"
            pool.sort(key=lambda x: (member_load.get(x, 0), x))
            selected = pool[0]
            used_in_day.add(selected)
            member_load[selected] = member_load.get(selected, 0) + 1
            return selected

        # 1. Gác trường học (T2 - T6)
        if d_vn not in ["Thứ 7", "Chủ nhật"]:
            for truong in DANH_SACH_TRUONG:
                cand = select_best(day_morning if day_morning else day_night_cax, allow_reuse=True)
                week_tasks.append({
                    "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                    "LoaiNhiemVu": f"Gác trường: {truong}", "Gio": "06-08h & 16-18h", "Diem": 1,
                    "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
                })

        # 2. Gác chốt cao điểm (3 chốt)
        for chot in DANH_SACH_CHOT:
            cand = select_best(day_morning if day_morning else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": f"Gác chốt: {chot}", "Gio": "06-08h & 16-18h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 3. Phối hợp tuần tra TTKS ban ngày (5 đ/c)
        for _ in range(5):
            cand = select_best(day_morning_nam if day_morning_nam else day_morning, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 4. Gác cổng ca ngày (4 ca đầu)
        for g_idx in range(min(4, len(list_gio))):
            cand = select_best(day_morning if day_morning else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Gác cổng", "Gio": list_gio[g_idx], "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 5. Tuần tra đêm C1 & C2
        for _ in range(4):
            cand = select_best(day_night_nam if day_night_nam else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })
        for _ in range(4):
            cand = select_best(day_night_nam if day_night_nam else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 6. Gác cổng ca đêm
        for g_idx in range(4, len(list_gio)):
            cand = select_best(day_night_nam if day_night_nam else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Gác cổng", "Gio": list_gio[g_idx], "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

    return pd.DataFrame(week_tasks)

# --- 7. GIAO DIỆN CHÍNH ---
tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM LỊCH NHIỆM VỤ", "⚙️ SẮP LỊCH TUẦN & TỪNG NGÀY", "✅ ĐIỂM DANH"])

# ==========================================
# TAB 1: XEM LỊCH NHIỆM VỤ
# ==========================================
with tab_view:
    c_hdr1, c_hdr2 = st.columns([7, 3])
    with c_hdr1:
        st.subheader(f"📌 LỊCH NHIỆM VỤ: {selected_week}")
    with c_hdr2:
        view_mode = st.radio("Chế độ xem:", ["Xem theo ngày", "Xem toàn bộ tuần"], horizontal=True)

    if view_mode == "Xem theo ngày":
        st.info(f"Đang hiển thị lịch chi tiết: **{selected_day_label}**")
        tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            tasks = tasks.copy()
            tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("🛡️ GÁC CỔNG TRỤ SỞ")
                g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng']
                st.table(g_df[["Gio", "HoTen", "Ấp"]])
            with col2:
                st.warning("🏫 CHỐT CAO ĐIỂM & TRƯỜNG HỌC")
                t_df = tasks[tasks['LoaiNhiemVu'].str.contains('Gác trường|Gác chốt', na=False)]
                st.table(t_df[["LoaiNhiemVu", "HoTen", "Ấp"]])
            with col3:
                st.error("🚔 TUẦN TRA & ĐỘT XUẤT")
                p_df = tasks[~tasks['LoaiNhiemVu'].str.contains('Gác cổng|Gác trường|Gác chốt', na=False)]
                st.table(p_df[["LoaiNhiemVu", "Gio", "HoTen", "Ấp"]])
        else:
            st.warning("Tuần này chưa có lịch nhiệm vụ được lưu. Chỉ huy vui lòng qua tab **SẮP LỊCH TUẦN** để tạo lịch.")
    else:
        week_all_tasks = df_history[df_history['Tuan'].astype(str) == str(selected_week)]
        if not week_all_tasks.empty:
            st.success(f"Tổng số phân công trong tuần: **{len(week_all_tasks)}** lượt nhiệm vụ.")
            st.dataframe(week_all_tasks[["Ngay", "LoaiNhiemVu", "Gio", "HoTen", "NgayThucTe"]], use_container_width=True, height=450)
        else:
            st.warning("Chưa có dữ liệu của tuần này.")

# ==========================================
# TAB 2: SẮP LỊCH TUẦN, ĐỘT XUẤT & TRỢ LÝ AI
# ==========================================
with tab_manage:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành ở cột bên trái để thực hiện phân công.")
    else:
        # 1. BỐ TRÍ FULL TUẦN (1 CHẠM)
        st.markdown(f"### 🚀 BỐ TRÍ TRỌN GÓI CHO CẢ TUẦN: **{selected_week}**")
        st.caption("Tự động cân đối điểm số, xoay đều quân số theo ca trực đã đăng ký, phân bổ toàn diện: Gác trường, Gác chốt, TTKS ngày, Gác cổng, Tuần tra đêm.")
        if st.button(f"⚡ BỐ TRÍ & LƯU TỰ ĐỘNG FULL CẢ TUẦN ({selected_week})", type="secondary", use_container_width=True):
            if df_curr_week.empty:
                st.error(f"Không tìm thấy dữ liệu đăng ký trực của '{selected_week}' trong bảng 'luutru'!")
            else:
                with st.spinner("Đang tính toán xoay tua quân số và ghi vào Google Sheets..."):
                    df_new_week = generate_balanced_week_schedule(selected_week, df_curr_week)
                    df_remain = df_history[df_history['Tuan'].astype(str) != str(selected_week)]
                    df_save_all = pd.concat([df_remain, df_new_week], ignore_index=True)
                    conn.update(worksheet="NhiemVu", data=df_save_all)
                    st.session_state["df_history"] = df_save_all
                    st.cache_data.clear()
                    st.success(f"✅ Đã bố trí thành công {len(df_new_week)} nhiệm vụ cho cả tuần {selected_week}!")
                    st.rerun()

        st.divider()

        # Dữ liệu ngày hiện tại để phục vụ AI và form
        current_saved = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        day_summary = current_saved.groupby("HoTen")["Diem"].sum().reset_index() if not current_saved.empty else pd.DataFrame(columns=["HoTen", "Diem"])

        def get_pool(target_names, is_dx=False):
            names_nam = [n for n in target_names if n not in LIST_NU]
            df_p = pd.DataFrame({"HoTen": names_nam}).merge(day_summary, on="HoTen", how="left").fillna(0)
            def set_prio(name):
                if name in night_cax_list: return 1
                if name in night_ap_list: return 2
                return 3
            df_p['Prio'] = df_p['HoTen'].apply(set_prio)
            df_p['StName'] = df_p['HoTen'].apply(lambda n: "Trực Xã" if n in night_cax_list else (f"Trực {dict_ap.get(n)}" if n in night_ap_list else "Trực Sáng"))
            if is_dx:
                df_p = df_p.sort_values(['Prio', 'Diem'], ascending=[True, True])
            else:
                df_p = df_p.sort_values(['Diem', 'Prio'], ascending=[True, True])
            df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - Đã làm: {int(r['Diem'])} ca", axis=1)
            return df_p

        pool_s = get_pool(morning_list)
        pool_d = get_pool(night_cax_list)
        pool_dx = get_pool(list(set(morning_list + night_cax_list + night_ap_list)), is_dx=True)

        # 2. KHUNG TRỢ LÝ AI TRA CỨU & ĐIỀU ĐỘNG ĐỘT XUẤT
        st.markdown(f"### 🤖 TRỢ LÝ ĐIỀU HÀNH & KIỂM TRA QUÂN SỐ TRONG NGÀY ({selected_day})")
        st.caption("Chỉ huy có thể hỏi trực tiếp AI xem hôm nay ai đã làm gì, ai đang rảnh hoặc nhờ AI gợi ý đồng chí thích hợp để canh giữ đối tượng đột xuất.")

        # Lập danh sách công việc thực tế của từng người trong ngày để cấp context cho AI
        current_tasks_summary = []
        if not current_saved.empty:
            for hoten, grp in current_saved.groupby("HoTen"):
                nv_list = grp.apply(lambda r: f"{r['LoaiNhiemVu']} ({r['Gio']})", axis=1).tolist()
                current_tasks_summary.append(f"- {hoten}: {', '.join(nv_list)} [Tổng: {len(nv_list)} ca]")
        tasks_context_str = "\n".join(current_tasks_summary) if current_tasks_summary else "Chưa có nhiệm vụ nào được phân công trong ngày này."

        if "manage_chat" not in st.session_state:
            st.session_state.manage_chat = [
                {"role": "assistant", "content": f"Chào chỉ huy, tôi đã nắm được toàn bộ nhiệm vụ của ngày **{selected_day_label}**. Chỉ huy cần kiểm tra quân số hoặc phân thêm ca **giữ đối tượng đột xuất** cứ nhắn cho tôi."}
            ]

        col_q1, col_q2 = st.columns(2)
        quick_query = None
        with col_q1:
            if st.button("🔍 Hôm nay ai đã làm những gì rồi?", use_container_width=True):
                quick_query = "Hãy liệt kê ngắn gọn, rõ ràng danh sách tất cả đồng chí đã được giao nhiệm vụ hôm nay và công việc cụ thể của từng người."
        with col_q2:
            if st.button("⚖️ Ai rảnh nhất để phân giữ đối tượng đột xuất?", use_container_width=True):
                quick_query = "Trong ngày hôm nay, ai hiện chưa có nhiệm vụ hoặc đang có ít ca nhất để tôi phân công canh giữ đối tượng đột xuất? Ưu tiên người trực Xã hoặc trực Sáng chưa bị quá tải."

        chat_container = st.container(height=260)
        with chat_container:
            for msg in st.session_state.manage_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_chat_input = st.chat_input("Nhập câu hỏi điều hành (VD: Cần 2 người giữ đối tượng lúc 14h-18h, gợi ý cho tôi ai hợp lý nhất...)")
        active_ai_prompt = quick_query if quick_query else user_chat_input

        if active_ai_prompt:
            st.session_state.manage_chat.append({"role": "user", "content": active_ai_prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(active_ai_prompt)
                with st.chat_message("assistant"):
                    with st.spinner("AI đang tra cứu lịch trực và đề xuất..."):
                        try:
                            model = get_working_gemini_model()
                            ai_sys = f"""
Bạn là Trợ lý Điều hành ANTTCS Bắc Tân Uyên.
Ngày đang xem: {selected_day_label} ({actual_date_str}).
DANH SÁCH NHIỆM VỤ ĐÃ PHÂN CÔNG HÔM NAY:
{tasks_context_str}

QUÂN SỐ ĐĂNG KÝ HÔM NAY:
- Trực Sáng: {morning_list}
- Trực Đêm Xã: {night_cax_list}
- Trực Đêm Ấp: {night_ap_list}
- Nữ miễn trực đêm/đối tượng phức tạp: {LIST_NU}

YÊU CẦU CỦA CHỈ HUY: "{active_ai_prompt}"

NGUYÊN TẮC TRẢ LỜI:
1. Trả lời thẳng thắn, rõ ràng, gạch đầu dòng ngắn gọn theo đúng tác phong công an.
2. Nếu chỉ huy cần bố trí "giữ đối tượng đột xuất": ưu tiên chọn những đồng chí chưa có ca hoặc ít ca nhất, tránh trùng khung giờ các ca đã giao.
"""
                            resp = model.generate_content(ai_sys)
                            st.markdown(resp.text)
                            st.session_state.manage_chat.append({"role": "assistant", "content": resp.text})
                        except Exception as e:
                            st.error(f"Lỗi AI: {e}")

        st.divider()

        # 3. FORM TINH CHỈNH CHI TIẾT TỪNG NGÀY & ĐỘT XUẤT
        st.markdown(f"### 🛠️ Điều chỉnh chi tiết theo ngày: **{selected_day_label}**")

        # Gác cổng
        st.markdown("#### 🛡️ 1. GÁC CỔNG TRỤ SỞ")
        c_gac1, c_gac2 = st.columns(2)
        g_day_res, g_night_res = [], []
        with c_gac1:
            st.caption("Gác cổng ban ngày (Ưu tiên Trực Sáng)")
            for i in range(min(4, len(list_gio))):
                gio = list_gio[i]
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                def_name = saved.iloc[0]['HoTen'] if not saved.empty else ""
                opts = ["-- Chưa chọn --"] + pool_s["HoTen"].tolist()
                def_i = opts.index(def_name) if def_name in opts else 0
                sel_m = st.selectbox(f"Ca {gio}", opts, index=def_i, key=f"g_d_{gio}_{selected_day}")
                if sel_m != "-- Chưa chọn --":
                    g_day_res.append({"HoTen": sel_m, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1})

        with c_gac2:
            st.caption("Gác cổng ban đêm (Ưu tiên Trực Đêm Xã)")
            for i in range(4, len(list_gio)):
                gio = list_gio[i]
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                def_name = saved.iloc[0]['HoTen'] if not saved.empty else ""
                opts = ["-- Chưa chọn --"] + pool_d["HoTen"].tolist()
                def_i = opts.index(def_name) if def_name in opts else 0
                sel_n = st.selectbox(f"Ca {gio}", opts, index=def_i, key=f"g_n_{gio}_{selected_day}")
                if sel_n != "-- Chưa chọn --":
                    g_night_res.append({"HoTen": sel_n, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1})

        # Chốt & trường
        st.markdown("#### 🏫 2. GÁC CHỐT CAO ĐIỂM & ĐIỀU TIẾT TRƯỜNG HỌC")
        col_c1, col_c2 = st.columns(2)
        cp_res = []
        with col_c1:
            for chot in DANH_SACH_CHOT:
                saved = current_saved[current_saved['LoaiNhiemVu'] == f"Gác chốt: {chot}"]
                def_name = saved.iloc[0]['HoTen'] if not saved.empty else ""
                opts = ["-- Chưa chọn --"] + pool_s["HoTen"].tolist()
                def_i = opts.index(def_name) if def_name in opts else 0
                sel = st.selectbox(f"Chốt: {chot}", opts, index=def_i, key=f"chot_{chot}_{selected_day}")
                if sel != "-- Chưa chọn --":
                    cp_res.append({"HoTen": sel, "LoaiNhiemVu": f"Gác chốt: {chot}", "Gio": "06-08h & 16-18h", "Diem": 1})

        with col_c2:
            if selected_day not in ["Thứ 7", "Chủ nhật"]:
                for tr in DANH_SACH_TRUONG:
                    saved = current_saved[current_saved['LoaiNhiemVu'] == f"Gác trường: {tr}"]
                    def_name = saved.iloc[0]['HoTen'] if not saved.empty else ""
                    opts = ["-- Chưa chọn --"] + pool_s["HoTen"].tolist()
                    def_i = opts.index(def_name) if def_name in opts else 0
                    sel = st.selectbox(f"{tr}", opts, index=def_i, key=f"tr_{tr}_{selected_day}")
                    if sel != "-- Chưa chọn --":
                        cp_res.append({"HoTen": sel, "LoaiNhiemVu": f"Gác trường: {tr}", "Gio": "06-08h & 16-18h", "Diem": 1})

        # Tuần tra
        st.markdown("#### 🚔 3. TUẦN TRA ĐÊM & TTKS BAN NGÀY")
        col_tt1, col_tt2, col_tt3 = st.columns(3)
        with col_tt1:
            saved_ttks = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra TTKS ban ngày']['HoTen'].tolist()
            ttks = st.multiselect("TTKS Ban ngày (5 người):", pool_s["Display"], default=[d for d in pool_s["Display"] if d.split(" (")[0] in saved_ttks], key=f"ms_ttks_{selected_day}")
        with col_tt2:
            saved_c1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
            tt1 = st.multiselect("Tuần tra C1 (18-22h - 4 người):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in saved_c1], key=f"ms_c1_{selected_day}")
        with col_tt3:
            saved_c2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
            tt2 = st.multiselect("Tuần tra C2 (22-02h - 4 người):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in saved_c2], key=f"ms_c2_{selected_day}")

        # 4. NHIỆM VỤ ĐỘT XUẤT (KHÔI PHỤC NGUYÊN BẢN ĐẦY ĐỦ)
        st.markdown("#### 🆘 4. NHIỆM VỤ ĐỘT XUẤT (Canh giữ đối tượng, Bảo vệ hiện trường, Áp giải...)")
        saved_dx = current_saved[current_saved['LoaiNhiemVu'].str.startswith('ĐX: ', na=False)]
        if not saved_dx.empty:
            unique_tasks = saved_dx.groupby('LoaiNhiemVu').agg({'Diem': 'first'}).reset_index()
            unique_tasks['TenViec'] = unique_tasks['LoaiNhiemVu'].str.replace('ĐX: ', '', regex=False)
            default_n_dx = len(unique_tasks)
        else:
            unique_tasks = pd.DataFrame(columns=['LoaiNhiemVu', 'Diem', 'TenViec'])
            default_n_dx = 1

        if 'n_dx' not in st.session_state:
            st.session_state.n_dx = default_n_dx

        c_btn1, c_btn2, _ = st.columns([2, 2, 8])
        with c_btn1:
            if st.button("➕ Thêm việc đột xuất", use_container_width=True):
                st.session_state.n_dx += 1
                st.rerun()
        with c_btn2:
            if st.button("➖ Bớt việc", use_container_width=True) and st.session_state.n_dx > 1:
                st.session_state.n_dx -= 1
                st.rerun()

        dx_res = []
        for i in range(st.session_state.n_dx):
            val_name, val_points, val_selected_mem = "", 1, []
            if i < len(unique_tasks):
                row_task = unique_tasks.iloc[i]
                val_name = row_task['TenViec']
                val_points = int(row_task['Diem'])
                saved_members = saved_dx[saved_dx['LoaiNhiemVu'] == row_task['LoaiNhiemVu']]['HoTen'].tolist()
                val_selected_mem = [d for d in pool_dx["Display"] if d.split(" (")[0] in saved_members]

            cx1, cx2, cx3 = st.columns([3, 5, 1])
            with cx1:
                t_n = st.text_input(f"Tên việc {i+1}", value=val_name if val_name else ("Giữ đối tượng đột xuất" if i == 0 and not val_name else ""), placeholder="VD: Giữ đối tượng ca 14h-18h", key=f"dxn_{i}_{selected_day}")
            with cx2:
                t_m = st.multiselect(f"Phân công quân số cho việc {i+1}", pool_dx["Display"], default=val_selected_mem, key=f"dxm_{i}_{selected_day}")
            with cx3:
                t_d = st.number_input(f"Điểm", 1, 10, value=val_points, key=f"dxd_{i}_{selected_day}")

            if t_n and t_m:
                for m in t_m:
                    dx_res.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})

        # NÚT LƯU PHƯƠNG ÁN TO, NỔI BẬT
        st.markdown('<div class="custom-save-btn">', unsafe_allow_html=True)
        if st.button(f"💾 LƯU PHƯƠNG ÁN NGÀY {selected_day_label.upper()} VÀO HỆ THỐNG", use_container_width=True, type="primary"):
            with st.spinner("Đang lưu toàn bộ phương án ngày vào Google Sheets..."):
                day_manual = g_day_res + g_night_res + cp_res + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1} for p in ttks] + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2] + \
                    dx_res

                df_m = pd.DataFrame(day_manual)
                df_m["Tuan"] = selected_week
                df_m["Ngay"] = selected_day
                df_m["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                df_m["NgayThucTe"] = actual_date_str

                df_final_save = pd.concat([
                    df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))],
                    df_m
                ], ignore_index=True)

                conn.update(worksheet="NhiemVu", data=df_final_save)
                st.session_state["df_history"] = df_final_save
                st.cache_data.clear()
                st.success(f"✅ ĐÃ LƯU THÀNH CÔNG TOÀN BỘ NHIỆM VỤ CHO {selected_day_label.upper()}!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 3: ĐIỂM DANH (GIỮ NGUYÊN)
# ==========================================
with tab_attendance:
    if not is_admin:
        st.warning("Vui lòng nhập Mã điều hành để điểm danh.")
    else:
        active_names = sorted(list(set(morning_list + night_cax_list + night_ap_list)))
        with st.form("form_att"):
            v_list = []
            for n in active_names:
                c1, c2, c3 = st.columns([3, 3, 4])
                c1.write(f"**{n}**")
                stt = c2.radio("TT", ["Có mặt", "Vắng"], key=f"at_{n}", horizontal=True, label_visibility="collapsed")
                re = c3.text_input("Lý do", key=f"ar_{n}", label_visibility="collapsed")
                if stt == "Vắng":
                    lt = [l for l, lst in [("Sáng", morning_list), ("Đêm Xã", night_cax_list), ("Đêm Ấp", night_ap_list)] if n in lst]
                    v_list.append({
                        "Tuan": selected_week, "Ngay": selected_day, "HoTen": n,
                        "TrangThai": "Vắng", "LyDo": re, "LoaiTruc": ", ".join(lt),
                        "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": actual_date_str
                    })
            if st.form_submit_button("💾 LƯU VẮNG", use_container_width=True):
                if v_list:
                    df_db = load_data(conn, URL_SHEET, "DiemDanh")
                    conn.update(worksheet="DiemDanh", data=pd.concat([df_db, pd.DataFrame(v_list)], ignore_index=True))
                    st.cache_data.clear()
                    st.success("Đã lưu điểm danh vắng!")
                    st.rerun()
                else:
                    st.success("Đầy đủ quân số!")

# ==========================================
# PHẦN CUỐI: TỔNG HỢP QUÂN SỐ NGUYÊN BẢN (CARD MÀU)
# ==========================================
st.divider()
st.markdown(f"### 👥 TỔNG HỢP QUÂN SỐ THEO LỊCH ĐĂNG KÝ ({selected_day_label})")
c_s, c_d, c_a = st.columns(3)
with c_s:
    st.markdown('☀️ TRỰC SÁNG', unsafe_allow_html=True)
    for n in morning_list:
        is_night = (n in night_cax_list)
        night_icon = " 🌙" if is_night else ""
        st.markdown(f'<div style="padding:4px 8px;margin-bottom:4px;background:#e8f4fd;border-radius:4px;">{n}{night_icon} <span style="font-size:12px;color:#666;">(Ấp: {dict_ap.get(n, "—")})</span></div>', unsafe_allow_html=True)
with c_d:
    st.markdown('🌙 TRỰC ĐÊM XÃ', unsafe_allow_html=True)
    for n in night_cax_list:
        st.markdown(f'<div style="padding:4px 8px;margin-bottom:4px;background:#fef3e2;border-radius:4px;">{n} <span style="font-size:12px;color:#666;">(Ấp: {dict_ap.get(n, "—")})</span></div>', unsafe_allow_html=True)
with c_a:
    st.markdown('🏡 TRỰC ĐÊM ẤP', unsafe_allow_html=True)
    for n in night_ap_list:
        st.markdown(f'<div style="padding:4px 8px;margin-bottom:4px;background:#edf7ed;border-radius:4px;">{n} <span style="font-size:12px;color:#666;">(Ấp: {dict_ap.get(n, "—")})</span></div>', unsafe_allow_html=True)
