import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Lịch trực ANTT", layout="wide", page_icon="📋")

# --- CSS TÙY CHỈNH ---
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 20px; border-radius: 12px; border-left: 8px solid #1E3A8A; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; min-height: 140px; }
    .name-text { color: #1E3A8A; font-size: 20px; font-weight: bold; }
    .location-tag { margin-top: 15px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 6px 12px; border-radius: 6px; display: inline-block; }
    .search-highlight { background-color: #FEF3C7; padding: 2px 5px; border-radius: 3px; border: 1px solid #F59E0B; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu từ Sheet Lưu Trữ
    # Dựa theo ảnh mới nhất: Cột A(Tuan), B(Ap), C(HoTen), D(T2_N)...
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="1727254590", skiprows=2)

    # Định nghĩa danh sách cột
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    
    df_raw.columns = cols[:len(df_raw.columns)]
    
    # Làm sạch dữ liệu
    df = df_raw.dropna(subset=['HoTen']).copy()
    # Chuyển các cột dấu 'x' về dạng chuẩn
    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # --- GIAO DIỆN CHÍNH ---
    st.title("📋 HỆ THỐNG TRA CỨU LỊCH TRỰC")

    # TÌM KIẾM NHANH THEO TÊN
    search_query = st.text_input("🔍 Nhập tên anh em để tìm nhanh (Ví dụ: Lập, Tình, Sĩ...):", "").strip().lower()

    if search_query:
        # Nếu có nhập ô tìm kiếm, hiển thị kết quả tìm kiếm trên toàn bộ dữ liệu
        st.subheader(f"🔎 Kết quả tìm kiếm cho: '{search_query}'")
        search_results = df[df['HoTen'].str.lower().str.contains(search_query, na=False)]
        
        if not search_results.empty:
            for _, row in search_results.iterrows():
                with st.expander(f"👤 {row['HoTen']} - {row['Ap']}"):
                    st.write(f"**Tuần:** {row['Tuan']}")
                    # Liệt kê các buổi trực của người này trong tuần đó
                    found_shifts = []
                    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
                    for idx, code in enumerate(day_codes):
                        if row[f"{code}_N"] == 'x': found_shifts.append(f"{days_vn[idx]} (Sáng - Tại CAX)")
                        if row[f"{code}_D_CAX"] == 'x': found_shifts.append(f"{days_vn[idx]} (Đêm - Tại CAX)")
                        if row[f"{code}_D_Ap"] == 'x': found_shifts.append(f"{days_vn[idx]} (Đêm - Tại Ấp)")
                    
                    if found_shifts:
                        for s in found_shifts: st.write(f"✅ {s}")
                    else:
                        st.write("Chưa có lịch trực trong tuần này.")
        else:
            st.warning("Không tìm thấy tên nhân sự này.")
        st.divider()

    # --- BỘ LỌC SIDEBAR THEO NGÀY GIỜ ---
    st.sidebar.header("📅 LỌC THEO THỜI GIAN")
    list_weeks = df['Tuan'].unique().tolist()
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks)

    list_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", list_days)
    
    selected_shift = st.sidebar.radio("Chọn ca trực:", ["Sáng", "Đêm"], horizontal=True)

    # Xử lý lọc theo ca
    day_map = dict(zip(list_days, day_codes))
    d = day_map[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    if selected_shift == "Sáng":
        on_duty = df_week[df_week[f"{d}_N"] == 'x']
    else:
        on_duty = df_week[(df_week[f"{d}_D_CAX"] == 'x') | (df_week[f"{d}_D_Ap"] == 'x')]

    # HIỂN THỊ DANH SÁCH
    st.markdown(f'<div class="time-box">📅 Tuần: {selected_week}</div>', unsafe_allow_html=True)
    st.subheader(f"🚩 Danh sách: {selected_day} - Ca {selected_shift}")

    if not on_duty.empty:
        grid = st.columns(3)
        for idx, (_, row) in enumerate(on_duty.iterrows()):
            with grid[idx % 3]:
                if selected_shift == "Sáng":
                    vi_tri = "Tại Công an xã"
                else:
                    vi_tri = "Tại Công an xã" if row[f"{d}_D_CAX"] == 'x' else f"Tại Ấp ({row['Ap']})"
                
                st.markdown(f"""
                    <div class="duty-card">
                        <div class="name-text">{row['HoTen']}</div>
                        <div class="info-text">🏠 <b>Đơn vị:</b> {row['Ap']}</div>
                        <div class="location-tag">📍 {vi_tri}</div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.warning(f"Không có dữ liệu trực.")

except Exception as e:
    st.error(f"Lỗi: {e}")
