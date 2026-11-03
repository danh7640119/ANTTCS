import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import google.generativeai as genai
import json
import re

# --- 1. CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide", page_icon="🛡️")

# CSS tạo kiểu nút bấm to nổi bật và màu sắc chỉ huy
st.markdown("""
<style>
    /* Nút lưu phương án to, viền nổi và màu nổi bật */
    div.stButton > button[kind="primary"] {
        font-size: 18px !important;
        font-weight: 700 !important;
        padding: 14px 28px !important;
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
        margin-top: 20px;
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

# Danh mục gác chốt & trường học cố định theo văn bản
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

# Nếu từ Thứ 3 trở đi, mặc định ưu tiên chọn tuần kế tiếp (chốt lịch tuần mới)
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
selected_day_label = st.sidebar.selectbox("Ngày trực:", day_options, index=0 if selected_week != list_tuan[current_week_idx] else cur_weekday)
selected_day = selected_day_label.split(" (")[0]
actual_date_str = day_to_actual_date[selected_day_label]

st.sidebar.divider()
st.sidebar.subheader("⏰ Tùy chỉnh ca gác")
default_times = "07-10h, 10-13h, 13-15h, 15-17h, 17-20h, 20-23h, 23-01h, 01-03h, 03-05h, 05-07h"
custom_times_str = st.sidebar.text_area("Danh sách giờ (cách nhau dấu phẩy):", value=default_times)
list_gio = [t.strip() for t in custom_times_str.split(",") if t.strip()]

# Dữ liệu quân số của ngày đang chọn
d_code = dict(zip(days_vn, day_codes))[selected_day]
df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

# --- 6. HÀM XẾP LỊCH FULL TUẦN (MẶC ĐỊNH GÁC CHỐT, TRƯỜNG, CỔNG, TUẦN TRA) ---
def auto_schedule_full_week(week_name, df_week_pool):
    member_load = {name: 0 for name in df_week_pool['HoTen'].unique()}
    week_tasks = []

    for day_idx, d_vn in enumerate(days_vn):
        c_code = day_codes[day_idx]
        act_date = (week_start_date + timedelta(days=day_idx)).strftime('%Y-%m-%d') if week_start_date else datetime.now().strftime('%Y-%m-%d')

        s_list = df_week_pool[df_week_pool[f"{c_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        d_cax = df_week_pool[df_week_pool[f"{c_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

        s_nam = [n for n in s_list if n not in LIST_NU]
        d_cax_nam = [n for n in d_cax if n not in LIST_NU]

        used_today = set()

        def pick_cand(pool, allow_dup=False):
            avail = [p for p in pool if p not in used_today]
            if not avail and allow_dup:
                avail = pool
            if not avail:
                return "Chưa phân"
            avail.sort(key=lambda x: (member_load.get(x, 0), x))
            chosen = avail[0]
            used_today.add(chosen)
            member_load[chosen] = member_load.get(chosen, 0) + 1
            return chosen

        # 1. Gác trường học (mặc định Thứ 2 - Thứ 6)
        if d_vn not in ["Thứ 7", "Chủ nhật"]:
            for tr in DANH_SACH_TRUONG:
                c = pick_cand(s_list if s_list else d_cax, allow_dup=True)
                week_tasks.append({
                    "Tuan": week_name, "Ngay": d_vn, "HoTen": c,
                    "LoaiNhiemVu": f"Gác trường: {tr}", "Gio": "06-08h & 16-18h", "Diem": 1,
                    "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
                })

        # 2. Gác chốt cao điểm (mặc định 3 chốt)
        for chot in DANH_SACH_CHOT:
            c = pick_cand(s_list if s_list else d_cax, allow_dup=True)
            week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": c,
                "LoaiNhiemVu": f"Gác chốt: {chot}", "Gio": "06-08h & 16-18h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 3. TTKS ban ngày (5 đ/c)
        for _ in range(5):
            c = pick_cand(s_nam if s_nam else s_list, allow_dup=True)
            week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": c,
                "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 4. Gác cổng trụ sở (4 ca ngày ưu tiên Sáng, các ca đêm ưu tiên Đêm Xã)
        for g_idx, gio in enumerate(list_gio):
            p = s_list if g_idx < 4 else (d_cax_nam if d_cax_nam else d_cax)
            c = pick_cand(p, allow_dup=True)
            week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": c,
                "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 5. Tuần tra đêm C1 & C2 (mỗi ca 4 đ/c)
        for _ in range(4):
            c = pick_cand(d_cax_nam if d_cax_nam else d_cax, allow_dup=True)
            week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": c,
                "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })
        for _ in range(4):
            c = pick_cand(d_cax_nam if d_cax_nam else d_cax, allow_dup=True)
            week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": c,
                "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

    return pd.DataFrame(week_tasks)

# --- 7. GIAO DIỆN CHÍNH ---
tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG & TRỢ LÝ AI", "✅ ĐIỂM DANH"])

# ==========================================
# TAB 1: XEM NHIỆM VỤ (GIỮ NGUYÊN CẤU TRÚC GỐC)
# ==========================================
with tab_view:
    st.subheader(f"📌 LỊCH PHÂN CÔNG: {selected_day_label} - {selected_week}")
    tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
    if not tasks.empty:
        tasks = tasks.copy()
        tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
        c1, c2 = st.columns(2)
        with c1:
            st.info("🛡️ GÁC CỔNG")
            g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng']
            st.table(g_df[["Gio", "HoTen", "Ấp"]])
        with c2:
            st.warning("🚔 TUẦN TRA & ĐỘT XUẤT (GỒM CẢ CHỐT / TRƯỜNG)")
            st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Ấp"]])
    else:
        st.info("Chưa có dữ liệu phân công cho ngày này. Vui lòng sang Tab 'Phân công' để tạo lịch.")

# ==========================================
# TAB 2: PHÂN CÔNG CHI TIẾT & TRỢ LÝ AI (THEO ĐÚNG CŨ)
# ==========================================
with tab_manage:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành tại thanh bên trái để sử dụng phân công.")
    else:
        # NÚT XẾP LỊCH FULL TUẦN NHANH (MẶC ĐỊNH CHỐT, TRƯỜNG, CỔNG, TUẦN TRA)
        st.markdown(f"### 🚀 BỐ TRÍ TRỌN GÓI CẢ TUẦN: **{selected_week}**")
        st.caption("Tự động xoay đều quân số theo ca trực đã đăng ký, phân bổ toàn bộ: Gác trường, Gác chốt, TTKS ngày, Gác cổng, Tuần tra đêm.")
        if st.button(f"⚡ BỐ TRÍ & LƯU TỰ ĐỘNG FULL CẢ TUẦN ({selected_week})", type="secondary", use_container_width=True):
            if df_curr_week.empty:
                st.error(f"Không tìm thấy dữ liệu đăng ký trực của '{selected_week}' trong bảng 'luutru'!")
            else:
                with st.spinner("Đang tính toán xoay tua quân số và ghi vào Google Sheets..."):
                    df_new_week = auto_schedule_full_week(selected_week, df_curr_week)
                    df_remain = df_history[df_history['Tuan'].astype(str) != str(selected_week)]
                    df_save_all = pd.concat([df_remain, df_new_week], ignore_index=True)
                    conn.update(worksheet="NhiemVu", data=df_save_all)
                    st.session_state["df_history"] = df_save_all
                    st.cache_data.clear()
                    st.success(f"✅ Đã bố trí thành công {len(df_new_week)} nhiệm vụ cho cả tuần {selected_week}!")
                    st.rerun()

        st.divider()

        # Dữ liệu phục vụ phân công trong ngày
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
            df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - Đã phân: {int(r['Diem'])}đ", axis=1)
            return df_p

        pool_s = get_pool(morning_list)
        pool_d = get_pool(night_cax_list)
        pool_dx = get_pool(list(set(morning_list + night_cax_list + night_ap_list)), is_dx=True)

        # ----------------------------------------------------
        # KHU VỰC CHATBOX AI ĐIỀU HÀNH & TRA CỨU QUÂN SỐ
        # ----------------------------------------------------
        st.markdown(f"### 🤖 TRỢ LÝ ĐIỀU HÀNH & KIỂM TRA QUÂN SỐ ({selected_day})")

        current_tasks_summary = []
        if not current_saved.empty:
            for hoten, grp in current_saved.groupby("HoTen"):
                nv_list = grp.apply(lambda r: f"{r['LoaiNhiemVu']} ({r['Gio']})", axis=1).tolist()
                current_tasks_summary.append(f"- {hoten}: {', '.join(nv_list)}")
        tasks_context_str = "\n".join(current_tasks_summary) if current_tasks_summary else "Chưa có nhiệm vụ nào được phân trong ngày này."

        if "manage_chat" not in st.session_state:
            st.session_state.manage_chat = [
                {"role": "assistant", "content": f"Chào chỉ huy, tôi đã nắm danh sách nhiệm vụ **{selected_day_label}**. Chỉ huy có thể bấm nút kiểm tra nhanh bên dưới hoặc hỏi ai rảnh để chia thêm ca **giữ đối tượng đột xuất**."}
            ]

        col_q1, col_q2 = st.columns(2)
        quick_query = None
        with col_q1:
            if st.button("🔍 Hôm nay ai đã làm những gì rồi?", use_container_width=True):
                quick_query = "Hãy liệt kê ngắn gọn danh sách các đồng chí đã được giao nhiệm vụ hôm nay và công việc cụ thể của từng người."
        with col_q2:
            if st.button("⚖️ Ai rảnh nhất để phân giữ đối tượng đột xuất?", use_container_width=True):
                quick_query = "Trong ngày hôm nay, ai hiện chưa có nhiệm vụ hoặc đang ít ca nhất để tôi phân công canh giữ đối tượng đột xuất? Tránh trùng ca đang gác."

        chat_container = st.container(height=240)
        with chat_container:
            for msg in st.session_state.manage_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_query = st.chat_input("Nhập câu hỏi (VD: Cần 2 người giữ đối tượng ca 14h-17h, ai phù hợp nhất...)")
        active_prompt = quick_query if quick_query else user_query

        if active_prompt:
            st.session_state.manage_chat.append({"role": "user", "content": active_prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(active_prompt)
                with st.chat_message("assistant"):
                    with st.spinner("AI đang tra cứu dữ liệu..."):
                        try:
                            model = get_working_gemini_model()
                            ai_sys = f"""
Bạn là Trợ lý Điều hành ANTTCS Bắc Tân Uyên.
Ngày: {selected_day_label} ({actual_date_str}).
DANH SÁCH NHIỆM VỤ ĐÃ PHÂN CÔNG HÔM NAY:
{tasks_context_str}

QUÂN SỐ TRỰC HÔM NAY:
- Trực Sáng: {morning_list}
- Trực Đêm Xã: {night_cax_list}
- Trực Đêm Ấp: {night_ap_list}
- Nữ miễn trực đêm: {LIST_NU}

YÊU CẦU: "{active_prompt}"
Trả lời ngắn gọn, thẳng thắn, rõ ràng theo tác phong chỉ huy công an.
"""
                            resp = model.generate_content(ai_sys)
                            st.markdown(resp.text)
                            st.session_state.manage_chat.append({"role": "assistant", "content": resp.text})
                        except Exception as err:
                            st.error(f"Lỗi AI: {err}")

        st.divider()

        # ----------------------------------------------------
        # FORM PHÂN CÔNG CHI TIẾT (GIỮ ĐÚNG NGUYÊN BẢN BAN ĐẦU)
        # ----------------------------------------------------
        # 1. GÁC CỔNG
        st.subheader("🛡️ 1. GÁC CỔNG")
        g_res = []
        cg1, cg2 = st.columns(2)
        for i, gio in enumerate(list_gio):
            p_df = pool_s if i < 4 else pool_d
            saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
            widget_key = f"gac_{gio}_{selected_day}"
            if widget_key not in st.session_state:
                idx = 0
                if not saved.empty and not p_df.empty:
                    saved_name = saved.iloc[0]['HoTen']
                    m = p_df[p_df['HoTen'].astype(str).str.strip() == str(saved_name).strip()]
                    if not m.empty:
                        idx = p_df.index.get_loc(m.index[0])
                st.session_state[widget_key] = p_df["Display"].iloc[idx] if not p_df.empty else ""
            with (cg1 if i % 2 == 0 else cg2):
                if not p_df.empty:
                    if st.session_state[widget_key] not in p_df["Display"].values:
                        st.session_state[widget_key] = p_df["Display"].iloc[0]
                    sel = st.selectbox(f"Ca {gio}", p_df["Display"], key=widget_key)
                    g_res.append({"HoTen": sel.split(" (")[0], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1})

        # 2. TUẦN TRA (TÙY BIẾN LINH HOẠT THEO YÊU CẦU)
        st.subheader("🚔 2. TUẦN TRA (Mặc định gợi ý 4 người - Có thể thêm/bớt tùy ý)")
        tt1_key = f"ms_tt1_{selected_day}"
        if tt1_key not in st.session_state:
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
            st.session_state[tt1_key] = [d for d in pool_d["Display"] if d.split(" (")[0] in def_tt1]

        tt2_key = f"ms_tt2_{selected_day}"
        if tt2_key not in st.session_state:
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
            st.session_state[tt2_key] = [d for d in pool_d["Display"] if d.split(" (")[0] in def_tt2]

        ct1, ct2 = st.columns(2)
        with ct1:
            tt1 = st.multiselect("Ca 1 (18-22h):", pool_d["Display"], key=tt1_key)
        with ct2:
            tt2 = st.multiselect("Ca 2 (22-02h):", pool_d["Display"], key=tt2_key)

        # 3. ĐỘT XUẤT (GIỮ ĐỐI TƯỢNG, BẢO VỆ HIỆN TRƯỜNG...)
        st.subheader("🆘 3. ĐỘT XUẤT (Ưu tiên Xã > Ấp)")
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
            if st.button("➕ Thêm việc", use_container_width=True):
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
                t_n = st.text_input(f"Việc {i+1}", value=val_name if val_name else ("Giữ đối tượng đột xuất" if i == 0 and not val_name else ""), placeholder="VD: Giữ đối tượng ca chiều", key=f"dxn_{i}_{selected_day}")
            with cx2:
                t_m = st.multiselect(f"Quân {i+1}", pool_dx["Display"], default=val_selected_mem, key=f"dxm_{i}_{selected_day}")
            with cx3:
                t_d = st.number_input(f"Đ", 1, 10, value=val_points, key=f"dxd_{i}_{selected_day}")

            if t_n and t_m:
                for m in t_m:
                    dx_res.append({"HoTen": m.split(" (")[0], "LoaiNhiemVu": f"ĐX: {t_n}", "Gio": "Đột xuất", "Diem": t_d})

        # NÚT LƯU PHƯƠNG ÁN TO, MÀU NỔI BẬT
        st.markdown('<div class="custom-save-btn">', unsafe_allow_html=True)
        if st.button(f"💾 LƯU PHƯƠNG ÁN NGÀY {selected_day_label.upper()}", use_container_width=True, type="primary"):
            with st.spinner("Đang lưu dữ liệu vào Google Sheets..."):
                # Giữ nguyên các nhiệm vụ cố định (Gác chốt, Gác trường, TTKS ngày) đã phân của ngày này
                fixed_tasks = current_saved[current_saved['LoaiNhiemVu'].str.contains('Gác chốt|Gác trường|Tuần tra TTKS ban ngày', na=False)].to_dict('records')

                final = fixed_tasks + g_res + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2] + \
                        dx_res

                df_s = pd.DataFrame(final)
                df_s["Tuan"] = selected_week
                df_s["Ngay"] = selected_day
                df_s["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                df_s["NgayThucTe"] = actual_date_str

                df_save = pd.concat([
                    df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))],
                    df_s
                ], ignore_index=True)

                conn.update(worksheet="NhiemVu", data=df_save)
                st.session_state["df_history"] = df_save
                st.cache_data.clear()
                st.success("✅ Đã lưu phương án thành công!")
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
# PHẦN CUỐI: TỔNG QUAN QUÂN SỐ NGUYÊN BẢN (CARD MÀU)
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
