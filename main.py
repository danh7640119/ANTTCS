import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta
import google.generativeai as genai
import json
import re

# --- 1. CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide", page_icon="🛡️")

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

# --- 4. TÍNH TOÁN NGÀY THỰC TẾ & NHẬN DIỆN TUẦN SAU ---
def parse_week_start(week_str):
    today = date.today()
    match = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", str(week_str))
    if match:
        d1, m1 = int(match.group(1)), int(match.group(2))
        # Dự đoán năm nếu chuyển giao năm
        yr = today.year
        return date(yr, m1, d1)
    return None

list_tuan = df_mem['Tuan'].dropna().unique().tolist()[::-1]

# Tìm tuần hiện tại và tuần kế tiếp
today = date.today()
current_week_idx = 0
next_week_idx = 0

for i, w in enumerate(list_tuan):
    st_date = parse_week_start(w)
    if st_date:
        if st_date <= today <= st_date + timedelta(days=6):
            current_week_idx = i
            # Nếu danh sách tuần mới nhất nằm ở đầu danh sách
            next_week_idx = max(0, i - 1)
            break

# --- 5. SIDEBAR ---
st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
access_key = st.sidebar.text_input("Mã điều hành:", type="password")
is_admin = (access_key == ADMIN_PASSWORD)

st.sidebar.markdown("### 📅 Chọn Tuần Kế Hoạch")
# Mặc định gợi ý tuần đang chọn: nếu hôm nay là Thứ 3 trở đi, chỉ huy thường chuẩn bị cho tuần sau
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

# --- 6. THUẬT TOÁN XOAY ĐỀU QUÂN SỐ CẢ TUẦN TỪ THỨ 2 ĐẾN CHỦ NHẬT ---
def generate_balanced_week_schedule(week_str, df_week_pool):
    """
    Phân bổ hợp lý toàn bộ tuần cho lực lượng ANTTCS:
    - Ca Sáng: Gác trường (7 điểm, T2-T6), Chốt cao điểm (3 điểm), TTKS giao thông ban ngày (5 đ/c), Gác cổng ban ngày (ca 1-4).
    - Ca Đêm Xã: Tuần tra đêm C1 (18-22h, 4 đ/c), Tuần tra đêm C2 (22-02h, 4 đ/c), Gác cổng đêm (ca 5-10).
    - Cân bằng số lượt phân công trong cả tuần, ưu tiên người ít ca trước.
    """
    member_load = {name: 0 for name in df_week_pool['HoTen'].unique()}
    week_tasks = []

    for day_idx, d_vn in enumerate(days_vn):
        c_code = day_codes[day_idx]
        if week_start_date:
            act_date = (week_start_date + timedelta(days=day_idx)).strftime('%Y-%m-%d')
        else:
            act_date = datetime.now().strftime('%Y-%m-%d')

        day_morning = df_week_pool[df_week_pool[f"{c_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        day_night_cax = df_week_pool[df_week_pool[f"{c_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        day_night_ap = df_week_pool[df_week_pool[f"{c_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

        # Lọc nam giới cho ca đêm và TTKS cơ động
        day_morning_nam = [n for n in day_morning if n not in LIST_NU]
        day_night_nam = [n for n in day_night_cax if n not in LIST_NU]

        used_in_day = set()

        def select_best(candidates, allow_reuse=False):
            pool = [c for c in candidates if c not in used_in_day]
            if not pool and allow_reuse:
                pool = candidates
            if not pool:
                return "Chưa đủ quân số"
            # Ưu tiên đồng chí có tổng số nhiệm vụ trong tuần thấp nhất
            pool.sort(key=lambda x: (member_load.get(x, 0), x))
            selected = pool[0]
            used_in_day.add(selected)
            member_load[selected] = member_load.get(selected, 0) + 1
            return selected

        # A. CÁC NHIỆM VỤ BAN NGÀY (Ưu tiên lấy từ danh sách Trực Sáng)
        # 1. Gác trường học (Thứ 2 - Thứ 6: 7 trường)
        if d_vn not in ["Thứ 7", "Chủ nhật"]:
            for truong in DANH_SACH_TRUONG:
                cand = select_best(day_morning if day_morning else day_night_cax, allow_reuse=True)
                week_tasks.append({
                    "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                    "LoaiNhiemVu": f"Gác trường: {truong}", "Gio": "06-08h & 16-18h", "Diem": 1,
                    "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
                })

        # 2. Gác chốt cao điểm (3 chốt: Ngã ba Cây Trắc, KCN, TTHC)
        for chot in DANH_SACH_CHOT:
            cand = select_best(day_morning if day_morning else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": f"Gác chốt: {chot}", "Gio": "06-08h & 16-18h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 3. Phối hợp tuần tra kiểm soát giao thông ban ngày (5 đ/c)
        for _ in range(5):
            cand = select_best(day_morning_nam if day_morning_nam else day_morning, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 4. Gác cổng trụ sở các ca ngày (4 ca đầu: 07h-17h)
        for g_idx in range(min(4, len(list_gio))):
            cand = select_best(day_morning if day_morning else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Gác cổng", "Gio": list_gio[g_idx], "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # B. CÁC NHIỆM VỤ BAN ĐÊM (Ưu tiên lấy từ danh sách Trực Đêm Xã)
        # 5. Tuần tra đêm Ca 1 (18-22h: 4 đ/c)
        for _ in range(4):
            cand = select_best(day_night_nam if day_night_nam else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 6. Tuần tra đêm Ca 2 (22-02h: 4 đ/c)
        for _ in range(4):
            cand = select_best(day_night_nam if day_night_nam else day_night_cax, allow_reuse=True)
            week_tasks.append({
                "Tuan": week_str, "Ngay": d_vn, "HoTen": cand,
                "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 7. Gác cổng trụ sở các ca đêm còn lại (từ ca thứ 5 trở đi)
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
# TAB 1: XEM NHIỆM VỤ (THEO NGÀY HOẶC THEO CẢ TUẦN)
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
# TAB 2: SẮP LỊCH TUẦN & TÙY CHỈNH NGÀY
# ==========================================
with tab_manage:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành ở cột bên trái để thực hiện phân công.")
    else:
        # 1. KHU VỰC PHÂN LỊCH FULL TUẦN (1 CHẠM CHO TUẦN SAU HOẶC TUẦN NÀY)
        st.markdown(f"### 🚀 BỐ TRÍ TRỌN GÓI CHO CẢ TUẦN: **{selected_week}**")
        st.caption("Thuật toán tự động đọc bảng `luutru`, tính toán xoay tua công bằng toàn bộ lực lượng ANTTCS, phân đầy đủ: Gác trường (7 điểm), Gác chốt (3 điểm), TTKS ban ngày (5 đ/c), Gác cổng (10 ca), Tuần tra đêm C1 & C2.")

        col_run1, col_run2 = st.columns([4, 6])
        with col_run1:
            btn_generate_full = st.button(f"⚡ BỐ TRÍ & LƯU FULL TUẦN ({selected_week})", type="primary", use_container_width=True)
            if btn_generate_full:
                if df_curr_week.empty:
                    st.error(f"Không tìm thấy dữ liệu đăng ký trực của '{selected_week}' trong bảng 'luutru'!")
                else:
                    with st.spinner("Đang tính toán xoay tua quân số và lưu vào Google Sheets..."):
                        df_new_week = generate_balanced_week_schedule(selected_week, df_curr_week)
                        # Xóa bỏ lịch cũ của tuần này (nếu có) và ghi đè lịch mới
                        df_remain = df_history[df_history['Tuan'].astype(str) != str(selected_week)]
                        df_save_all = pd.concat([df_remain, df_new_week], ignore_index=True)

                        conn.update(worksheet="NhiemVu", data=df_save_all)
                        st.session_state["df_history"] = df_save_all
                        st.cache_data.clear()
                        st.success(f"✅ Đã bố trí thành công {len(df_new_week)} nhiệm vụ cho cả tuần {selected_week}!")
                        st.rerun()

        st.divider()

        # 2. KHU VỰC ĐIỀU CHỈNH CHI TIẾT TỪNG NGÀY
        st.markdown(f"### 🛠️ Điều chỉnh chi tiết theo ngày: **{selected_day_label}**")
        current_saved = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        day_summary = current_saved.groupby("HoTen")["Diem"].sum().reset_index() if not current_saved.empty else pd.DataFrame(columns=["HoTen", "Diem"])

        def get_pool(target_names):
            names_nam = [n for n in target_names if n not in LIST_NU]
            df_p = pd.DataFrame({"HoTen": names_nam}).merge(day_summary, on="HoTen", how="left").fillna(0)
            df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} (Ấp: {dict_ap.get(r['HoTen'], '—')}) - {int(r['Diem'])} ca", axis=1)
            return df_p

        pool_s = get_pool(morning_list)
        pool_d = get_pool(night_cax_list)

        # Form tinh chỉnh
        c_gac1, c_gac2 = st.columns(2)
        with c_gac1:
            st.markdown("##### 🛡️ Gác cổng ban ngày (Ưu tiên trực Sáng)")
            g_day_res = []
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
            st.markdown("##### 🛡️ Gác cổng ban đêm (Ưu tiên trực Đêm Xã)")
            g_night_res = []
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
        st.markdown("##### 🏫 Gác chốt cao điểm & Trường học")
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
        st.markdown("##### 🚔 Tuần tra kiểm soát & Tuần tra đêm")
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

        st.write("")
        if st.button("💾 LƯU THAY ĐỔI RIÊNG CHO NGÀY NÀY", use_container_width=True):
            with st.spinner("Đang cập nhật ngày vào hệ thống..."):
                day_manual = g_day_res + g_night_res + cp_res + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1} for p in ttks] + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                    [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2]

                df_m = pd.DataFrame(day_manual)
                df_m["Tuan"] = selected_week
                df_m["Ngay"] = selected_day
                df_m["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                df_m["NgayThucTe"] = actual_date_str

                # Cập nhật riêng ngày được chỉnh
                df_final_save = pd.concat([
                    df_history[~((df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day))],
                    df_m
                ], ignore_index=True)

                conn.update(worksheet="NhiemVu", data=df_final_save)
                st.session_state["df_history"] = df_final_save
                st.cache_data.clear()
                st.success(f"✅ Đã cập nhật xong dữ liệu cho {selected_day_label}!")
                st.rerun()

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
