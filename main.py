import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT (CHỈ TỪ SECRETS) ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Streamlit Secrets!")
    st.stop()

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin: 15px 0; }
    .morning-card { padding: 8px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 5px; }
    .morning-night-card { padding: 8px; border-radius: 5px; border-left: 5px solid #F59E0B; background-color: #FEF3C7; margin-bottom: 5px; }
    .night-cax-card { padding: 8px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. ĐỌC DỮ LIỆU GỐC
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Đọc lịch sử nhiệm vụ
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành (Chỉ dành cho Chỉ huy):", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Chọn Tuần:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn Ngày:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'].astype(str) == str(selected_week)]
    
    m_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ (Công khai)", "⚙️ PHÂN CÔNG (Khóa)", "🔔 ĐIỂM DANH (Khóa)"])

    # --- TAB 1: XEM NHIỆM VỤ (CÔNG KHAI) ---
    with tab_view:
        st.subheader(f"📌 PHÂN CÔNG CHI TIẾT {selected_day} - TUẦN {selected_week}")
        # Ép kiểu string để tránh lỗi không tìm thấy dữ liệu
        tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        
        if not tasks.empty:
            tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ LỊCH GÁC CỔNG")
                g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                g_df['SortID'] = g_df['Gio'].map(GIO_ORDER)
                st.table(g_df.sort_values('SortID')[["Gio", "HoTen", "Ấp"]])
            with c2:
                st.warning("🚔 TUẦN TRA & ĐỘT XUẤT")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Ấp"]])
        else:
            st.info("Chưa có dữ liệu phân công chi tiết được lưu.")

    # --- TAB 2: PHÂN CÔNG (BẢO MẬT) ---
    with tab_manage:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập Mã điều hành ở thanh bên trái để thực hiện phân công.")
        else:
            st.subheader("⚙️ THIẾT LẬP NHIỆM VỤ CHI TIẾT")
            # --- [Copy toàn bộ logic phân công của bản V21/V22 vào đây] ---
            # Lưu ý: Khi lưu, nhớ ép kiểu Tuan thành string: df_s["Tuan"] = str(selected_week)
            st.write("Dán code phân công tại đây...")

    # --- TAB 3: ĐIỂM DANH (BẢO MẬT) ---
    with tab_attendance:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập Mã điều hành để thực hiện điểm danh và xem thống kê vắng.")
        else:
            st.subheader("🔔 ĐIỂM DANH QUÂN SỐ")
            # --- [Copy toàn bộ logic điểm danh và thống kê của bản V23 vào đây] ---
            st.write("Dán code điểm danh tại đây...")

    # --- QUÂN SỐ TỔNG QUAN (CÔNG KHAI) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TRONG NGÀY</div>', unsafe_allow_html=True)
    c_s, c_d, c_a = st.columns(3)
    with c_s:
        st.markdown("<p style='color:#2563EB; font-weight:bold; text-align:center;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in m_list:
            is_night = n in n_cax_list
            st.markdown(f'<div class="{"morning-night-card" if is_night else "morning-card"}"><div class="name-tag">{n} {"🌙" if is_night else ""}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)
    with c_d:
        st.markdown("<p style='color:#EA580C; font-weight:bold; text-align:center;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in n_cax_list: st.markdown(f'<div class="night-cax-card"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)
    with c_a:
        st.markdown("<p style='color:#16A34A; font-weight:bold; text-align:center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in n_ap_list: st.markdown(f'<div class="night-ap-card"><div class="name-tag">{n}</div><div class="ap-tag">Ấp: {dict_ap.get(n)}</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
