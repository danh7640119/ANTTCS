import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH & SECRETS ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Kiểm tra lại Streamlit Secrets!")
    st.stop()

# Cấu hình hệ thống
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}
TTL_2MIN = "2m" # Giới hạn request đến Google API mỗi 2 phút

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện
st.markdown("""
    <style>
    .morning-card { padding: 10px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 8px; }
    .night-cax-card { padding: 10px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 8px; }
    .night-ap-card { padding: 10px; border-radius: 5px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 8px; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- ĐỌC DỮ LIỆU (Dùng Cache 2 phút để tránh bị Google chặn) ---
    df_raw = conn.read(spreadsheet=URL_SHEET, worksheet="luutru", ttl=TTL_2MIN, skiprows=2)
    
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Lịch sử nhiệm vụ
    try:
        df_history = conn.read(spreadsheet=URL_SHEET, worksheet="NhiemVu", ttl=TTL_2MIN)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar điều hướng
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password", help="Chỉ dành cho chỉ huy trực")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    # --- CHIA TABS ---
    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT", "✅ ĐIỂM DANH"])

    # --- 1. TAB XEM NHIỆM VỤ (CÔNG KHAI) ---
    with tab_view:
        st.subheader(f"📌 LỊCH PHÂN CÔNG {selected_day} - TUẦN {selected_week}")
        tasks = df_history[(df_history['Tuan'].astype(str) == str(selected_week)) & (df_history['Ngay'] == selected_day)]
        
        if not tasks.empty:
            tasks['Ấp'] = tasks['HoTen'].map(dict_ap)
            c1, c2 = st.columns(2)
            with c1:
                st.info("🛡️ GÁC CỔNG")
                g_df = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                g_df['SortID'] = g_df['Gio'].map(GIO_ORDER)
                st.table(g_df.sort_values('SortID')[["Gio", "HoTen", "Ấp"]])
            with c2:
                st.warning("🚔 TUẦN TRA & ĐỘT XUẤT")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Ấp"]])
        else:
            st.info("Chưa có dữ liệu phân công chi tiết cho ngày này.")

    # --- 2. TAB PHÂN CÔNG (KHÓA) ---
    with tab_manage:
        if not is_admin:
            st.warning("⚠️ Vui lòng nhập Mã điều hành ở thanh bên để thực hiện phân công.")
        else:
            st.success("🔓 Chế độ Điều hành đã kích hoạt")
            # [Giữ nguyên logic phân công cũ của đồng chí ở đây]
            st.write("Thực hiện các thao tác điều động quân số tại đây.")

    # --- 3. TAB ĐIỂM DANH (KHÓA) ---
    with tab_attendance:
        if not is_admin:
            st.warning("⚠️ Quyền truy cập bị hạn chế. Vui lòng nhập Mã điều hành để thực hiện điểm danh.")
        else:
            st.subheader(f"✅ ĐIỂM DANH - {selected_day}")
            
            all_direct = []
            for n in morning_list: all_direct.append({"HoTen": n, "Loai": "Sáng"})
            for n in night_cax_list: all_direct.append({"HoTen": n, "Loai": "Đêm Xã"})
            for n in night_ap_list: all_direct.append({"HoTen": n, "Loai": "Đêm Ấp"})
            
            df_att_input = pd.DataFrame(all_direct).drop_duplicates(subset=['HoTen'])

            if not df_att_input.empty:
                with st.form("f_diemdanh"):
                    results = []
                    for _, row in df_att_input.iterrows():
                        col1, col2, col3 = st.columns([3, 3, 4])
                        col1.write(f"**{row['HoTen']}**")
                        stt = col2.radio("TT", ["Có mặt", "Vắng"], key=f"s_{row['HoTen']}", horizontal=True, label_visibility="collapsed")
                        re = col3.text_input("Lý do", key=f"r_{row['HoTen']}", placeholder="Lý do vắng...", label_visibility="collapsed")
                        
                        results.append({
                            "Tuan": selected_week, "Ngay": selected_day, "HoTen": row['HoTen'],
                            "TrangThai": stt, "LyDo": re if stt == "Vắng" else "",
                            "LoaiTruc": row['Loai'], "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                    
                    if st.form_submit_button("💾 LƯU BẢNG ĐIỂM DANH"):
                        try:
                            df_db = conn.read(spreadsheet=URL_SHEET, worksheet="DiemDanh", ttl=0)
                            df_final = pd.concat([df_db, pd.DataFrame(results)], ignore_index=True)
                            conn.update(worksheet="DiemDanh", data=df_final)
                            st.success("Đã cập nhật bảng điểm danh thành công!")
                        except:
                            st.error("Lỗi khi lưu dữ liệu. Kiểm tra lại Worksheet 'DiemDanh'")
            else:
                st.info("Không có dữ liệu quân số trực.")

    # --- QUÂN SỐ TỔNG QUAN (CÔNG KHAI) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    c_s, c_d, c_a = st.columns(3)
    with c_s:
        st.markdown("<p style='color:#2563EB; font-weight:bold;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in morning_list: st.markdown(f'<div class="morning-card"><b>{n}</b><br><small>Ấp: {dict_ap.get(n)}</small></div>', unsafe_allow_html=True)
    with c_d:
        st.markdown("<p style='color:#EA580C; font-weight:bold;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in night_cax_list: st.markdown(f'<div class="night-cax-card"><b>{n}</b><br><small>Ấp: {dict_ap.get(n)}</small></div>', unsafe_allow_html=True)
    with c_a:
        st.markdown("<p style='color:#16A34A; font-weight:bold;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list: st.markdown(f'<div class="night-ap-card"><b>{n}</b><br><small>Ấp: {dict_ap.get(n)}</small></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
