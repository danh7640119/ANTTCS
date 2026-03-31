import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .morning-card { padding: 10px; border-radius: 8px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 8px; }
    .night-cax-card { padding: 10px; border-radius: 8px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 8px; }
    .night-ap-card { padding: 10px; border-radius: 8px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 8px; }
    .double-duty-warning { background-color: #FEE2E2 !important; border: 2px solid #EF4444 !important; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 13px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 25px 0 15px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. ĐỌC DỮ LIỆU GỐC (Bảng luutru để lấy thông tin Ấp)
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()

    # Tạo từ điển tra cứu Ấp nhanh: { 'Tên': 'Ấp' }
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # 3. SIDEBAR & BỘ LỌC
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    # Danh sách quân số thực tế trong ngày
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG"])

    # --- TAB XEM (Hiển thị kèm Ấp) ---
    with tab_view:
        st.subheader(f"📌 NHIỆM VỤ NGÀY {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            # Thêm thông tin ấp vào bảng hiển thị
            tasks_display = tasks.copy()
            tasks_display['Ấp'] = tasks_display['HoTen'].map(dict_ap)
            
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ Gác Cổng")
                gac_v = tasks_display[tasks_display['LoaiNhiemVu'] == 'Gác cổng'].copy()
                gac_v['SortID'] = gac_v['Gio'].map(GIO_ORDER)
                st.table(gac_v.sort_values('SortID')[["Gio", "HoTen", "Ấp"]])
            with c2:
                st.warning("🚔 Tuần Tra & Đột Xuất")
                st.table(tasks_display[tasks_display['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Ấp"]])
        else: st.info("Chưa có lịch trực chi tiết.")

    # --- TAB PHÂN CÔNG (Hiển thị Ấp trong Selectbox) ---
    with tab_manage:
        if not is_admin:
            st.warning("Nhập mật mã để điều động.")
        else:
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
            
            def get_selection_pool(names):
                names_nam = [n for n in names if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0)
                df_p = df_p.sort_values("Diem", ascending=True)
                # ĐỊNH DẠNG MỚI: Tên (Ấp) - [Điểm]
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({dict_ap.get(r['HoTen'], 'N/A')}) - {int(r['Diem'])}đ", axis=1)
                return df_p

            pool_s = get_selection_pool(morning_list)
            pool_d = get_selection_pool(night_cax_list)
            
            # (Phần Selectbox Gác, Tuần tra dùng pool_s/pool_d tương tự V12)
            st.subheader("🛡️ PHÂN CÔNG CÔNG TÁC")
            # ... [Logic lặp Selectbox và Lưu tương tự bản trước] ...

    # --- 6. DANH SÁCH TỔNG (HIỂN THỊ KÈM ẤP DƯỚI TÊN) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN (KÈM ĐỊA BÀN)</div>', unsafe_allow_html=True)
    cs, cd, ca = st.columns(3)
    
    with cs:
        st.markdown("<p style='color:#2563EB; font-weight:bold; text-align:center;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in morning_list:
            is_warn = "double-duty-warning" if n in night_cax_list else ""
            ap_name = dict_ap.get(n, "N/A")
            st.markdown(f'''<div class="morning-card {is_warn}">
                            <div class="name-tag">{n}</div>
                            <div class="ap-tag">Đơn vị: {ap_name}</div>
                        </div>''', unsafe_allow_html=True)
    
    with cd:
        st.markdown("<p style='color:#EA580C; font-weight:bold; text-align:center;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in night_cax_list:
            is_warn = "double-duty-warning" if n in morning_list else ""
            ap_name = dict_ap.get(n, "N/A")
            st.markdown(f'''<div class="night-cax-card {is_warn}">
                            <div class="name-tag">{n}</div>
                            <div class="ap-tag">Đơn vị: {ap_name}</div>
                        </div>''', unsafe_allow_html=True)

    with ca:
        st.markdown("<p style='color:#16A34A; font-weight:bold; text-align:center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list:
            ap_name = dict_ap.get(n, "N/A")
            st.markdown(f'''<div class="night-ap-card">
                            <div class="name-tag">{n}</div>
                            <div class="ap-tag">Đơn vị: {ap_name}</div>
                        </div>''', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
