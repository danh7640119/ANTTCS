import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Lịch trực ANTT - Công an xã", layout="wide", page_icon="📋")

# --- THIẾT KẾ GIAO DIỆN (CSS) ---
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; font-size: 16px; }
    .duty-card { padding: 15px; border-radius: 12px; border-left: 8px solid #1E3A8A; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .double-duty { background-color: #FFFBEB; border-left: 8px solid #F59E0B; border: 2px solid #FDE68A; }
    .name-text { color: #1E3A8A; font-size: 18px; font-weight: bold; }
    .info-text { color: #4B5563; font-size: 14px; margin-top: 5px; }
    .location-tag { margin-top: 10px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 4px 10px; border-radius: 6px; display: inline-block; font-size: 13px; }
    .group-header { background-color: #1E3A8A; color: white; padding: 10px 15px; border-radius: 5px; margin-top: 25px; margin-bottom: 15px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }
    .count-badge { background-color: #FFFFFF; color: #1E3A8A; padding: 2px 10px; border-radius: 15px; font-size: 14px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

try:
    # --- KẾT NỐI DỮ LIỆU ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu từ Sheet "LuuTru"
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="1727254590", skiprows=2)

    # Định nghĩa cấu trúc cột (Tuan, Ap, HoTen + 3 cột/ngày x 7 ngày)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Làm sạch dữ liệu 'x' để so sánh chính xác
    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    st.title("📋 HỆ THỐNG QUẢN LÝ LỊCH TRỰC")

    # --- PHẦN 1: Ô TÌM KIẾM NHANH ---
    search_query = st.text_input("🔍 Nhập tên anh em để tra cứu lịch cá nhân:", placeholder="Ví dụ: Lập, Sĩ, Tình...").strip().lower()

    if search_query:
        search_results = df[df['HoTen'].str.lower().str.contains(search_query, na=False)]
        if not search_results.empty:
            st.info(f"Tìm thấy {len(search_results)} bản ghi cho từ khóa '{search_query}'")
            for _, row in search_results.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['Ap']} ({row['Tuan']})"):
                    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
                    found_any = False
                    for idx, code in enumerate(day_codes):
                        shifts = []
                        if row[f"{code}_N"] == 'x': shifts.append("Sáng (CAX)")
                        if row[f"{code}_D_CAX"] == 'x': shifts.append("Đêm (CAX)")
                        if row[f"{code}_D_Ap"] == 'x': shifts.append("Đêm (Ấp)")
                        
                        if shifts:
                            st.write(f"📅 **{days_vn[idx]}**: {', '.join(shifts)}")
                            found_any = True
                    if not found_any: st.write("Không có lịch trực trong tuần này.")
        else:
            st.warning("Không tìm thấy kết quả.")
        st.divider()

    # --- PHẦN 2: XÁC ĐỊNH THỜI GIAN THỰC ---
    now = datetime.now()
    today_date_str = now.strftime("%d/%m") # Định dạng ngày/tháng: 09/02
    today_weekday_idx = now.weekday()      # Thứ 2 là 0, CN là 6

    list_weeks = df['Tuan'].unique().tolist()
    
    # Tìm tuần hiện tại dựa trên ngày tháng
    default_week_idx = 0
    for i, week in enumerate(list_weeks):
        if today_date_str in str(week):
            default_week_idx = i
            break

    # --- PHẦN 3: BỘ LỌC SIDEBAR ---
    st.sidebar.header("📅 TÙY CHỌN THỜI GIAN")
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks, index=default_week_idx)
    
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=today_weekday_idx)
    
    selected_shift = st.sidebar.radio("Chọn ca trực:", ["Sáng", "Đêm"], horizontal=True)

    # --- PHẦN 4: LOGIC LỌC VÀ HIỂN THỊ ---
    day_map = dict(zip(days_vn, day_codes))
    d = day_map[selected_day]
    df_week = df[df['Tuan'] == selected_week]
    
    # Lấy danh sách trực sáng để kiểm tra trực kép (double duty)
    morning_list = df_week[df_week[f"{d}_N"] == 'x']['HoTen'].tolist()

    st.markdown(f'<div class="time-box">📍 Đang xem: {selected_week} | {selected_day} | Ca {selected_shift}</div>', unsafe_allow_html=True)

    if selected_shift == "Sáng":
        on_duty = df_week[df_week[f"{d}_N"] == 'x']
        st.markdown(f'<div class="group-header">DANH SÁCH TRỰC BAN NGÀY <span class="count-badge">{len(on_duty)} đ/c</span></div>', unsafe_allow_html=True)
        
        if not on_duty.empty:
            grid = st.columns(3)
            for idx, (_, row) in enumerate(on_duty.iterrows()):
                with grid[idx % 3]:
                    st.markdown(f"""<div class="duty-card"><div class="name-text">{row['HoTen']}</div><div class="info-text">🏠 Đơn vị: {row['Ap']}</div><div class="location-tag">📍 Tại Công an xã</div></div>""", unsafe_allow_html=True)
    else:
        # CA ĐÊM
        cax_duty = df_week[df_week[f"{d}_D_CAX"] == 'x']
        ap_duty = df_week[df_week[f"{d}_D_Ap"] == 'x']
        
        st.markdown(f'<div class="group-header">TỔNG QUÂN SỐ TRỰC ĐÊM <span class="count-badge">{len(cax_duty) + len(ap_duty)} đ/c</span></div>', unsafe_allow_html=True)

        st.markdown("#### 🏢 Nhóm trực tại Công an xã")
        if not cax_duty.empty:
            grid_cax = st.columns(3)
            for idx, (_, row) in enumerate(cax_duty.iterrows()):
                is_double = "double-duty" if row['HoTen'] in morning_list else ""
                note = "<br><small style='color:#B45309'>⚠️ <i>Có trực ca sáng</i></small>" if is_double else ""
                with grid_cax[idx % 3]:
                    st.markdown(f"""<div class="duty-card {is_double}"><div class="name-text">{row['HoTen']}</div><div class="info-text">🏠 Đơn vị: {row['Ap']}</div><div class="location-tag">📍 Tại Công an xã</div>{note}</div>""", unsafe_allow_html=True)
        
        st.markdown("#### 🏘️ Nhóm trực tại các Ấp")
        if not ap_duty.empty:
            grid_ap = st.columns(3)
            for idx, (_, row) in enumerate(ap_duty.iterrows()):
                is_double = "double-duty" if row['HoTen'] in morning_list else ""
                note = "<br><small style='color:#B45309'>⚠️ <i>Có trực ca sáng</i></small>" if is_double else ""
                with grid_ap[idx % 3]:
                    st.markdown(f"""<div class="duty-card {is_double}"><div class="name-text">{row['HoTen']}</div><div class="info-text">🏠 Đơn vị: {row['Ap']}</div><div class="location-tag">📍 Tại Ấp {row['Ap']}</div>{note}</div>""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Đã xảy ra lỗi: {e}")
    st.info("Mẹo: Hãy đảm bảo cột Tuần trong Google Sheets có chứa ngày tháng dạng dd/mm để hệ thống tự động nhận diện.")
