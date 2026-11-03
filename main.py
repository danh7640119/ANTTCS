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

# Danh sách nữ đồng chí miễn gác đêm / tuần tra
LIST_NU = [
    "Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương",
    "Huỳnh Thụy Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm", "Lê Thanh Tuyền"
]

# Danh mục các điểm trực cố định từ kế hoạch tuần
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

# --- 4. TÍNH TOÁN NGÀY THỰC TẾ ---
def parse_week_start(week_str):
    today = date.today()
    match = re.search(r"\((\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\)", str(week_str))
    if match:
        d1, m1 = int(match.group(1)), int(match.group(2))
        return date(today.year, m1, d1)
    return None

list_tuan = df_mem['Tuan'].dropna().unique().tolist()[::-1]
default_tuan_idx = 0
today = date.today()
for i, w in enumerate(list_tuan):
    st_date = parse_week_start(w)
    if st_date and (st_date <= today <= st_date + timedelta(days=6)):
        default_tuan_idx = i
        break

# --- 5. SIDEBAR ---
st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
access_key = st.sidebar.text_input("Mã điều hành:", type="password")
is_admin = (access_key == ADMIN_PASSWORD)

selected_week = st.sidebar.selectbox("Tuần trực:", list_tuan, index=default_tuan_idx)
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
selected_day_label = st.sidebar.selectbox("Ngày trực:", day_options, index=cur_weekday)
selected_day = selected_day_label.split(" (")[0]
actual_date_str = day_to_actual_date[selected_day_label]

st.sidebar.divider()
st.sidebar.subheader("⏰ Tùy chỉnh ca gác cổng")
default_times = "07-10h, 10-13h, 13-15h, 15-17h, 17-20h, 20-23h, 23-01h, 01-03h, 03-05h, 05-07h"
custom_times_str = st.sidebar.text_area("Danh sách giờ gác:", value=default_times)
list_gio = [t.strip() for t in custom_times_str.split(",") if t.strip()]

# Quân số ngày đang chọn
d_code = dict(zip(days_vn, day_codes))[selected_day]
df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

# --- 6. HÀM THUẬT TOÁN XOAY ĐỀU QUÂN SỐ CẢ TUẦN ---
def auto_schedule_full_week(week_name, df_week_data):
    """
    Tự động phân bổ đều toàn bộ lực lượng ANTTCS cho cả tuần theo điểm tích lũy:
    - Gác cổng (list_gio)
    - Trực chốt (3 điểm)
    - Trực trường học (7 trường, Thứ 2 - Thứ 6)
    - Tuần tra TTKS ban ngày (5 đ/c)
    - Tuần tra đêm C1 & C2 (mỗi ca 4 đ/c)
    """
    total_assigned_counts = {name: 0 for name in df_week_data['HoTen'].unique()}
    full_week_tasks = []

    for idx, d_vn in enumerate(days_vn):
        code = day_codes[idx]
        if week_start_date:
            act_date = (week_start_date + timedelta(days=idx)).strftime('%Y-%m-%d')
        else:
            act_date = datetime.now().strftime('%Y-%m-%d')

        s_list = df_week_data[df_week_data[f"{code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        d_cax = df_week_data[df_week_data[f"{code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        d_ap = df_week_data[df_week_data[f"{code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

        # Lọc danh sách nam cho ca đêm / tuần tra
        s_nam = [n for n in s_list if n not in LIST_NU]
        d_cax_nam = [n for n in d_cax if n not in LIST_NU]

        used_today = set()

        def pick_candidate(pool, prefer_low=True):
            available = [p for p in pool if p not in used_today]
            if not available:
                available = pool  # Nếu thiếu quân thì cho phép trùng
            if not available:
                return "Chưa phân"
            # Sắp xếp theo số ca đã phân trong tuần (càng ít càng ưu tiên)
            available.sort(key=lambda x: total_assigned_counts.get(x, 0))
            chosen = available[0]
            used_today.add(chosen)
            total_assigned_counts[chosen] = total_assigned_counts.get(chosen, 0) + 1
            return chosen

        # 1. Gác cổng (4 ca đầu ưu tiên Sáng, sau đó Đêm Xã)
        for g_idx, gio in enumerate(list_gio):
            pool = s_list if g_idx < 4 else (d_cax_nam if d_cax_nam else d_cax)
            worker = pick_candidate(pool)
            full_week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": worker,
                "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 2. Gác chốt cao điểm (3 chốt)
        for chot in DANH_SACH_CHOT:
            worker = pick_candidate(s_list if s_list else d_cax)
            full_week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": worker,
                "LoaiNhiemVu": f"Gác chốt: {chot}", "Gio": "06-08h & 16-18h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 3. Gác trường học (Thứ 2 đến Thứ 6)
        if d_vn not in ["Thứ 7", "Chủ nhật"]:
            for truong in DANH_SACH_TRUONG:
                worker = pick_candidate(s_list if s_list else d_cax)
                full_week_tasks.append({
                    "Tuan": week_name, "Ngay": d_vn, "HoTen": worker,
                    "LoaiNhiemVu": f"Gác trường: {truong}", "Gio": "06-08h & 16-18h", "Diem": 1,
                    "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
                })

        # 4. Tuần tra TTKS ban ngày (5 đ/c)
        for _ in range(5):
            worker = pick_candidate(s_nam if s_nam else s_list)
            full_week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": worker,
                "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

        # 5. Tuần tra đêm C1 & C2 (mỗi ca 4 đ/c)
        for _ in range(4):
            worker = pick_candidate(d_cax_nam if d_cax_nam else d_cax)
            full_week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": worker,
                "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })
        for _ in range(4):
            worker = pick_candidate(d_cax_nam if d_cax_nam else d_cax)
            full_week_tasks.append({
                "Tuan": week_name, "Ngay": d_vn, "HoTen": worker,
                "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1,
                "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M"), "NgayThucTe": act_date
            })

    return pd.DataFrame(full_week_tasks)

# --- 7. GIAO DIỆN CHÍNH ---
tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG & TRỢ LÝ AI", "✅ ĐIỂM DANH"])

# ==========================================
# TAB 1: XEM NHIỆM VỤ
# ==========================================
with tab_view:
    st.subheader(f"📌 LỊCH PHÂN CÔNG: {selected_day_label} - {selected_week}")
    tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
    if not tasks.empty:
        tasks = tasks.copy()
        tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("🛡️ GÁC CỔNG")
            g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng']
            st.table(g_df[["Gio", "HoTen", "Ấp"]])
        with c2:
            st.warning("🏫 GÁC TRƯỜNG & CHỐT ĐIỀU TIẾT")
            t_df = tasks[tasks['LoaiNhiemVu'].str.contains('Gác trường|Gác chốt', na=False)]
            st.table(t_df[["LoaiNhiemVu", "HoTen", "Ấp"]])
        with c3:
            st.error("🚔 TUẦN TRA & ĐỘT XUẤT")
            p_df = tasks[~tasks['LoaiNhiemVu'].str.contains('Gác cổng|Gác trường|Gác chốt', na=False)]
            st.table(p_df[["LoaiNhiemVu", "Gio", "HoTen", "Ấp"]])
    else:
        st.info("Chưa có dữ liệu phân công cho ngày này. Vui lòng sang Tab 'Phân công' để tạo lịch.")

# ==========================================
# TAB 2: PHÂN CÔNG CHI TIẾT & TRỢ LÝ AI
# ==========================================
with tab_manage:
    if not is_admin:
        st.warning("🔒 Vui lòng nhập Mã điều hành tại thanh bên trái để sử dụng phân công.")
    else:
        # NÚT XẾP LỊCH FULL TUẦN NHANH
        st.markdown("### 🚀 PHÂN LỊCH TỰ ĐỘNG FULL TUẦN (XOAY ĐỀU QUÂN)")
        col_w1, col_w2 = st.columns([4, 6])
        with col_w1:
            if st.button("⚡ TỰ ĐỘNG XẾP LỊCH FULL CẢ TUẦN", type="primary", use_container_width=True):
                with st.spinner("Đang tính toán xoay tua quân số và lưu toàn bộ tuần vào Google Sheets..."):
                    df_full_new = auto_schedule_full_week(selected_week, df_curr_week)
                    # Giữ lại các tuần khác, thay thế toàn bộ tuần đang chọn
                    df_remain = df_history[df_history['Tuan'].astype(str) != str(selected_week)]
                    df_updated = pd.concat([df_remain, df_full_new], ignore_index=True)
                    conn.update(worksheet="NhiemVu", data=df_updated)
                    st.session_state["df_history"] = df_updated
                    st.success(f"✅ Đã phân bổ và lưu thành công toàn bộ {len(df_full_new)} lượt phân công cho {selected_week}!")
                    st.rerun()
        with col_w2:
            st.caption("ℹ️ Thuật toán tự động cân đối điểm, xoay đều tất cả các đ/c ANTTCS theo ca Sáng/Đêm đã đăng ký trong tuần, đủ các nhiệm vụ: Gác cổng, 3 Chốt cao điểm, 7 Trường học, TTKS ban ngày và Tuần tra đêm.")

        st.divider()

        # PHÂN BỔ CHI TIẾT THEO NGÀY
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
            df_p = df_p.sort_values(['Diem', 'Prio'], ascending=[True, True])
            df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({r['StName']}) - Đã phân: {int(r['Diem'])}đ", axis=1)
            return df_p

        pool_s = get_pool(morning_list)
        pool_d = get_pool(night_cax_list)
        pool_dx = get_pool(list(set(morning_list + night_cax_list + night_ap_list)), is_dx=True)

        st.subheader(f"🎯 Phân công chi tiết cho: {selected_day_label}")

        # 1. GÁC CỔNG
        st.markdown("#### 🛡️ 1. GÁC CỔNG")
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

        # 2. GÁC CHỐT VÀ TRƯỜNG HỌC
        st.markdown("#### 🏫 2. GÁC CHỐT CAO ĐIỂM & ĐIỀU TIẾT TRƯỜNG HỌC")
        cp1, cp2 = st.columns(2)
        chot_res = []
        with cp1:
            st.caption("🚦 Chốt cao điểm (06-08h & 16-18h)")
            for chot in DANH_SACH_CHOT:
                k_chot = f"chot_{chot}_{selected_day}"
                saved = current_saved[current_saved['LoaiNhiemVu'] == f"Gác chốt: {chot}"]
                def_name = saved.iloc[0]['HoTen'] if not saved.empty else ""
                options = ["-- Chưa chọn --"] + pool_s["HoTen"].tolist()
                def_idx = options.index(def_name) if def_name in options else 0
                sel_chot = st.selectbox(f"Chốt {chot}:", options, index=def_idx, key=k_chot)
                if sel_chot != "-- Chưa chọn --":
                    chot_res.append({"HoTen": sel_chot, "LoaiNhiemVu": f"Gác chốt: {chot}", "Gio": "06-08h & 16-18h", "Diem": 1})
        with cp2:
            st.caption("🎒 Trường học (Thứ 2 - Thứ 6)")
            if selected_day not in ["Thứ 7", "Chủ nhật"]:
                for truong in DANH_SACH_TRUONG:
                    k_tr = f"tr_{truong}_{selected_day}"
                    saved = current_saved[current_saved['LoaiNhiemVu'] == f"Gác trường: {truong}"]
                    def_name = saved.iloc[0]['HoTen'] if not saved.empty else ""
                    options = ["-- Chưa chọn --"] + pool_s["HoTen"].tolist()
                    def_idx = options.index(def_name) if def_name in options else 0
                    sel_tr = st.selectbox(f"{truong}:", options, index=def_idx, key=k_tr)
                    if sel_tr != "-- Chưa chọn --":
                        chot_res.append({"HoTen": sel_tr, "LoaiNhiemVu": f"Gác trường: {truong}", "Gio": "06-08h & 16-18h", "Diem": 1})
            else:
                st.info("Cuối tuần không có lịch trực trường học.")

        # 3. TUẦN TRA
        st.markdown("#### 🚔 3. TUẦN TRA ĐÊM & TTKS BAN NGÀY")
        ct1, ct2, ct3 = st.columns(3)
        with ct1:
            saved_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
            tt1_key = f"ms_tt1_{selected_day}"
            tt1 = st.multiselect("Tuần tra C1 (18-22h):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in saved_tt1], key=tt1_key)
        with ct2:
            saved_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
            tt2_key = f"ms_tt2_{selected_day}"
            tt2 = st.multiselect("Tuần tra C2 (22-02h):", pool_d["Display"], default=[d for d in pool_d["Display"] if d.split(" (")[0] in saved_tt2], key=tt2_key)
        with ct3:
            saved_ttks = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra TTKS ban ngày']['HoTen'].tolist()
            ttks_key = f"ms_ttks_{selected_day}"
            ttks = st.multiselect("TTKS Ban ngày (3 ca):", pool_s["Display"], default=[d for d in pool_s["Display"] if d.split(" (")[0] in saved_ttks], key=ttks_key)

        st.write("")
        if st.button("💾 LƯU PHƯƠNG ÁN NGÀY NÀY", use_container_width=True, type="primary"):
            with st.spinner("Đang lưu dữ liệu ngày vào Google Sheets..."):
                final = g_res + chot_res + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 1} for p in tt1] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 1} for p in tt2] + \
                        [{"HoTen": p.split(" (")[0], "LoaiNhiemVu": "Tuần tra TTKS ban ngày", "Gio": "3 ca ngày", "Diem": 1} for p in ttks]
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
                st.success("✅ Đã lưu phương án thành công!")
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
