import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH BẢO MẬT ---
ADMIN_PASSWORD = "13579" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"] 

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide", page_icon="👮")

# CSS giữ nguyên để đảm bảo giao diện đẹp
st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 12px; border-radius: 10px; border-left: 6px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .double-duty { background-color: #FFFBEB; border-left: 6px solid #F59E0B; border: 2px solid #FDE68A; }
    .name-text { color: #1E3A8A; font-size: 16px; font-weight: bold; }
    .location-tag { margin-top: 5px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 2px 8px; border-radius: 4px; display: inline-block; font-size: 12px; }
    .group-header { background-color: #1E3A8A; color: white; padding: 10px; border-radius: 5px; margin: 15px 0; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

try:
    # --- 2. KẾT NỐI & TẢI DỮ LIỆU DÙNG CHUNG (LUÔN CHẠY) ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc lịch trực gốc
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()
    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # Đọc lịch sử nhiệm vụ (Để tính điểm cuốn chiếu)
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. ĐIỀU KHIỂN SIDEBAR ---
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    st.sidebar.divider()
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # --- 4. PHÂN CHIA TAB ---
    tab_view, tab_manage = st.tabs(["📋 XEM LỊCH TRỰC", "⚡ PHÂN LỊCH CHI TIẾT"])

    with tab_view:
        st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day}</div>', unsafe_allow_html=True)
        
        # Hiển thị Card quân số (Sáng/Đêm) - Công khai ai cũng xem được
        col1, col2 = st.columns(2)
        morning_list = df_week[df_week[f"{d_code}_N"] == 'x']['HoTen'].tolist()
        night_cax_list = df_week[df_week[f"{d_code}_D_CAX"] == 'x']['HoTen'].tolist()
        night_ap_list = df_week[df_week[f"{d_code}_D_Ap"] == 'x']['HoTen'].tolist()

        with col1:
            st.markdown('<div class="group-header">☀️ TRỰC SÁNG</div>', unsafe_allow_html=True)
            for name in morning_list:
                is_db = "double-duty" if (name in night_cax_list or name in night_ap_list) else ""
                st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{name}</div></div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="group-header">🌙 TRỰC ĐÊM</div>', unsafe_allow_html=True)
            for name in night_cax_list:
                is_db = "double-duty" if name in morning_list else ""
                st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{name} (Xã)</div></div>', unsafe_allow_html=True)
            for name in night_ap_list:
                st.markdown(f'<div class="duty-card"><div class="name-text">{name} (Ấp)</div></div>', unsafe_allow_html=True)

        # Hiển thị kết quả phân công đã lưu
        if not df_history.empty:
            saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            if not saved.empty:
                st.divider()
                st.subheader("📌 CHI TIẾT PHÂN CÔNG NHIỆM VỤ")
                st.dataframe(saved[["Gio", "HoTen", "LoaiNhiemVu", "Diem"]], use_container_width=True)

    with tab_manage:
        if not is_admin:
            st.error("🔒 Vui lòng nhập mã điều hành ở Sidebar để thực hiện phân công.")
            st.stop() # Dừng Tab này tại đây nếu ko có pass
        
        st.success("✅ Đã mở khóa quyền Điều hành")
        
        # --- LOGIC TÍNH TOÁN QUÂN SỐ PHÂN CÔNG (Chỉ chạy khi có Pass) ---
        summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
        
        # Lọc danh sách Nam trực Xã
        list_sang_nam = [n for n in morning_list if n not in LIST_NU]
        list_dem_nam = [n for n in night_cax_list if n not in LIST_NU]
        
        # Sắp xếp cuốn chiếu
        df_sang_prio = pd.DataFrame({"HoTen": list_sang_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
        df_dem_prio = pd.DataFrame({"HoTen": list_dem_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")

        # --- GIAO DIỆN PHÂN CÔNG ---
        st.subheader("🛡️ Gác cổng (Xoay vòng theo điểm)")
        CA_GAC = [
            ("07-10h", 1, "S"), ("10-13h", 1, "S"), ("13-15h", 1, "S"), ("15-17h", 1, "S"),
            ("17-20h", 2, "D"), ("20-23h", 2, "D"), ("23-01h", 2, "D"), ("01-03h", 2, "D"), ("03-05h", 2, "D"), ("05-07h", 2, "D")
        ]
        
        col_g1, col_g2 = st.columns(2)
        final_gac = []
        for i, (gio, diem, loai) in enumerate(CA_GAC):
            pool = df_sang_prio["HoTen"].tolist() if loai == "S" else df_dem_prio["HoTen"].tolist()
            with (col_g1 if i < 5 else col_g2):
                if pool:
                    sel = st.selectbox(f"Ca {gio}", pool, index=i%len(pool), key=f"sel_g_{i}")
                    final_gac.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": diem})
        
        st.divider()
        st.subheader("🚔 Tuần tra & Phát sinh")
        c_tt1, c_tt2 = st.columns(2)
        with c_tt1:
            tt1 = st.multiselect("Tuần tra C1 (18-22h):", df_dem_prio["HoTen"].tolist())
        with c_tt2:
            tt2 = st.multiselect("Tuần tra C2 (22-02h):", df_dem_prio["HoTen"].tolist())
            
        ps_name = st.text_input("Nhiệm vụ phát sinh (Giữ đối tượng...):")
        ps_mem = st.multiselect("Đồng chí thực hiện:", df['HoTen'].unique().tolist())
        ps_diem = st.number_input("Điểm thưởng:", 1, 10, 3)

        if st.button("💾 LƯU PHÂN CÔNG VÀO HỆ THỐNG", use_container_width=True, type="primary"):
            # Logic gom data và ghi đè conn.update như cũ
            new_data = []
            new_data.extend(final_gac)
            for p in tt1: new_data.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
            for p in tt2: new_data.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
            if ps_name and ps_mem:
                for p in ps_mem: new_data.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_diem})
            
            df_save = pd.DataFrame(new_data)
            df_save["Tuan"] = selected_week
            df_save["Ngay"] = selected_day
            df_save["NgayTao"] = datetime.now().strftime("%d/%m/%Y")
            
            # Cập nhật lên Sheet
            updated_df = pd.concat([df_history, df_save], ignore_index=True)
            conn.update(worksheet="NhiemVu", data=updated_df)
            st.success("✅ Đã lưu thành công! Hãy quay lại Tab 'XEM LỊCH TRỰC' để kiểm tra.")
            st.balloons()

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
