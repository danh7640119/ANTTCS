import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    st.error("⚠️ LỖI: Chưa cấu hình 'admin_password' trong Streamlit Secrets!")
    st.stop()

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS Giao diện (Xanh/Vàng/Cam)
st.markdown("""
    <style>
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 15px 0; text-transform: uppercase; }
    .morning-card { padding: 8px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 5px; }
    .morning-night-card { padding: 8px; border-radius: 5px; border-left: 5px solid #F59E0B; background-color: #FEF3C7; margin-bottom: 5px; }
    .night-cax-card { padding: 8px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 5px; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. ĐỌC DỮ LIỆU GỐC (Bảng luutru)
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # 3. ĐỌC LỊCH SỬ NHIỆM VỤ (Bảng NhiemVu)
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar điều hướng
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    # Ép kiểu tuần về string để tránh lỗi lệch kiểu dữ liệu
    list_weeks = [str(w) for w in df_mem['Tuan'].unique().tolist()[::-1]]
    selected_week = st.sidebar.selectbox("Tuần trực:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    # Lọc quân số trong ngày (Sáng, Đêm, Ấp)
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    # Quan trọng: Ép kiểu so sánh chuỗi
    df_curr_week = df_mem[df_mem['Tuan'].astype(str) == selected_week]
    
    m_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    n_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "🔔 ĐIỂM DANH"])

    # --- TAB 1: XEM NHIỆM VỤ (CÔNG KHAI) ---
    with tab_view:
        st.subheader(f"📌 CHI TIẾT NHIỆM VỤ: {selected_day} - TUẦN {selected_week}")
        # Lọc chính xác từ bảng NhiemVu
        tasks = df_history[(df_history['Tuan'].astype(str) == selected_week) & (df_history['Ngay'] == selected_day)]
        
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
            st.info(f"Chưa có dữ liệu phân công chi tiết cho {selected_day}. Chỉ huy vui lòng vào Tab 'Phân công' để thiết lập.")

    # --- TAB 2: PHÂN CÔNG (BẢO MẬT) ---
    with tab_manage:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành để thực hiện phân công nhiệm vụ.")
        else:
            st.subheader("⚙️ THIẾT LẬP NHIỆM VỤ CHI TIẾT")
            # Phần này dán lại logic chọn Multiselect và nút Lưu của bạn
            st.write("--- Chế độ chỉnh sửa đang mở ---")
            # [Logic phân công giữ nguyên từ bản V21]

    # --- TAB 3: ĐIỂM DANH (BẢO MẬT) ---
    with tab_attendance:
        if not is_admin:
            st.warning("🔒 Vui lòng nhập mã điều hành để điểm danh quân số.")
        else:
            st.subheader(f"🔔 ĐIỂM DANH {selected_day}")
            # Gom quân số tổng
            all_today = []
            for n in m_list: all_today.append({"HoTen": n, "Ca": "Sáng"})
            for n in n_cax_list: all_today.append({"HoTen": n, "Ca": "Đêm Xã"})
            for n in n_ap_list: all_today.append({"HoTen": n, "Ca": "Trực Ấp"})
            df_att = pd.DataFrame(all_today).drop_duplicates(subset=['HoTen'])

            if not df_att.empty:
                df_att['Vắng'] = False
                df_att['Lý do'] = ""
                edited = st.data_editor(df_att, hide_index=True, use_container_width=True, key="att_v26")
                
                if st.button("💾 LƯU ĐIỂM DANH", type="primary"):
                    save_att = edited.copy()
                    save_att['TrangThai'] = save_att['Vắng'].apply(lambda x: "Vắng" if x else "Có mặt")
                    save_att['Tuan'] = selected_week
                    save_att['Ngay'] = selected_day
                    save_att['NgayTao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    try:
                        old_att = conn.read(spreadsheet=url, worksheet="DiemDanh", ttl=0)
                        old_att = old_att[~((old_att['Tuan'].astype(str) == selected_week) & (old_att['Ngay'] == selected_day))]
                        final_save = pd.concat([old_att, save_att[["Tuan", "Ngay", "HoTen", "TrangThai", "Lý do", "Ca", "NgayTao"]]], ignore_index=True)
                    except:
                        final_save = save_att
                    
                    conn.update(worksheet="DiemDanh", data=final_save)
                    st.success("Đã lưu điểm danh thành công!")
                    st.rerun()

    # --- QUÂN SỐ TỔNG QUAN (CÔNG KHAI) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TRONG NGÀY</div>', unsafe_allow_html=True)
    if not any([m_list, n_cax_list, n_ap_list]):
        st.error(f"❌ Không tìm thấy danh sách trực trong bảng 'luutru' cho Tuần {selected_week} - {selected_day}. Vui lòng kiểm tra lại Google Sheets.")
    else:
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
    st.error(f"Lỗi kết nối hoặc dữ liệu: {e}")
