import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Điều hành ANTT", layout="wide", page_icon="👮")

st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 12px; border-radius: 10px; border-left: 6px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .double-duty { background-color: #FFFBEB; border-left: 6px solid #F59E0B; border: 2px solid #FDE68A; }
    .name-text { color: #1E3A8A; font-size: 16px; font-weight: bold; }
    .location-tag { margin-top: 5px; font-weight: bold; color: #059669; background-color: #ECFDF5; padding: 2px 8px; border-radius: 4px; display: inline-block; font-size: 12px; }
    .group-header { background-color: #1E3A8A; color: white; padding: 10px; border-radius: 5px; margin: 15px 0; font-weight: bold; }
    .section-title { color: #1E3A8A; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin-top: 25px; margin-bottom: 15px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DANH SÁCH ĐỒNG CHÍ NỮ (Cần cập nhật tên chính xác) ---
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"] 

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu trực gốc
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="luutru", skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    for col in df.columns[3:]:
        df[col] = df[col].astype(str).str.strip().str.lower()

    # Đọc lịch sử điểm (Sheet NhiemVu)
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 2. XỬ LÝ THỜI GIAN ---
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    now = datetime.now()
    today_str = now.strftime("%d/%m")
    default_week_idx = next((i for i, w in enumerate(list_weeks) if today_str in str(w)), 0)

    # --- 3. BỘ LỌC SIDEBAR ---
    st.sidebar.header("📅 QUẢN LÝ LỊCH")
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks, index=default_week_idx)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=now.weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # --- 4. HIỂN THỊ DANH SÁCH TRỰC (GIỮ MÀU SẮC CŨ) ---
    st.title("👮 HỆ THỐNG CHỈ HUY TÁC CHIẾN")
    st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day}</div>', unsafe_allow_html=True)
    
    # Lấy danh sách để so sánh màu sắc
    morning_duty_list = df_week[df_week[f"{d_code}_N"] == 'x']['HoTen'].tolist()
    night_cax_list = df_week[df_week[f"{d_code}_D_CAX"] == 'x']['HoTen'].tolist()
    night_ap_list = df_week[df_week[f"{d_code}_D_Ap"] == 'x']['HoTen'].tolist()
    total_night_list = night_cax_list + night_ap_list

    col_list_1, col_list_2 = st.columns(2)

    with col_list_1:
        st.markdown('<div class="group-header">☀️ DANH SÁCH TRỰC SÁNG</div>', unsafe_allow_html=True)
        df_morning = df_week[df_week[f"{d_code}_N"] == 'x']
        if not df_morning.empty:
            for _, r in df_morning.iterrows():
                # Nếu trực sáng mà có tên trong danh sách trực đêm (Xã hoặc Ấp) -> Màu vàng
                is_db = "double-duty" if r['HoTen'] in total_night_list else ""
                st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{r["HoTen"]}</div><div class="location-tag">📍 Tại Công an xã</div></div>', unsafe_allow_html=True)

    with col_list_2:
        st.markdown('<div class="group-header">🌙 DANH SÁCH TRỰC ĐÊM</div>', unsafe_allow_html=True)
        # Hiển thị trực Xã trước
        for name in night_cax_list:
            is_db = "double-duty" if name in morning_duty_list else ""
            st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{name}</div><div class="location-tag">🏢 Tại Công an xã</div></div>', unsafe_allow_html=True)
        # Hiển thị trực Ấp
        for name in night_ap_list:
            is_db = "double-duty" if name in morning_duty_list else ""
            st.markdown(f'<div class="duty-card {is_db}"><div class="name-text">{name}</div><div class="location-tag">🏘️ Tại Ấp</div></div>', unsafe_allow_html=True)

    # --- 5. CHUẨN BỊ QUÂN SỐ CHO PHÂN CÔNG (CUỐN CHIẾU) ---
    summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
    
    # Nhóm Sáng (Không Nữ) -> Gác 7-17h
    list_sang_nam = [n for n in morning_duty_list if n not in LIST_NU]
    df_sang_prio = pd.DataFrame({"HoTen": list_sang_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
    
    # Nhóm Đêm Xã (Không Nữ) -> Gác 17-7h & Tuần tra
    list_dem_cax_nam = [n for n in night_cax_list if n not in LIST_NU]
    df_dem_prio = pd.DataFrame({"HoTen": list_dem_cax_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
    
    # --- 6. KHU VỰC PHÂN CÔNG (NẰM DƯỚI) ---
    st.markdown('<h2 class="section-title">⚡ PHÂN CÔNG CHI TIẾT & CHẤM ĐIỂM</h2>', unsafe_allow_html=True)
    
    # GÁC CỔNG
    st.subheader("🛡️ Lịch Gác Cổng (Cuốn chiếu theo điểm)")
    CA_GAC = [
        ("07:00-10:00", 1, "SANG"), ("10:00-13:00", 1, "SANG"), ("13:00-15:00", 1, "SANG"), ("15:00-17:00", 1, "SANG"),
        ("17:00-20:00", 2, "DEM"), ("20:00-23:00", 2, "DEM"), ("23:00-01:00", 2, "DEM"), ("01:00-03:00", 2, "DEM"), 
        ("03:00-05:00", 2, "DEM"), ("05:00-07:00", 2, "DEM")
    ]
    
    final_gac = []
    c_g1, c_g2 = st.columns(2)
    for i, (gio, diem, loai) in enumerate(CA_GAC):
        pool = df_sang_prio["HoTen"].tolist() if loai == "SANG" else df_dem_prio["HoTen"].tolist()
        with (c_g1 if i < 5 else c_g2):
            if not pool:
                st.warning(f"Ca {gio}: Trống quân số!")
                sel = "N/A"
            else:
                # Tự động gợi ý người ít điểm nhất (index xoay vòng)
                sel = st.selectbox(f"Ca {gio} ({loai})", pool, index=i%len(pool), key=f"g_{i}")
            final_gac.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": diem})

    # TUẦN TRA
    st.markdown('<h3 class="section-title">🚔 Tuần tra đêm (Chỉ đ/c trực Xã)</h3>', unsafe_allow_html=True)
    col_tt1, col_tt2 = st.columns(2)
    pool_tt = df_dem_prio["HoTen"].tolist()
    with col_tt1:
        tt1 = st.multiselect("Ca 1 (18h-22h):", pool_tt, default=pool_tt[:4] if len(pool_tt)>=4 else pool_tt)
    with col_tt2:
        tt2 = st.multiselect("Ca 2 (22h-02h):", pool_tt, default=pool_tt[4:8] if len(pool_tt)>=8 else [])

    # PHÁT SINH
    st.markdown('<h3 class="section-title">🆘 Nhiệm vụ phát sinh (Tất cả quân số)</h3>', unsafe_allow_html=True)
    list_all_duty = df_week['HoTen'].unique().tolist()
    c_ps1, c_ps2, c_ps3 = st.columns([2,1,1])
    with c_ps1: ps_name = st.text_input("Tên việc:")
    with c_ps2: ps_mem = st.multiselect("Đồng chí thực hiện:", list_all_duty)
    with c_ps3: ps_d = st.number_input("Điểm:", 1, 10, 3)

    # --- 7. NÚT LƯU ---
    if st.button("💾 XÁC NHẬN VÀ LƯU TOÀN BỘ PHÂN CÔNG", use_container_width=True, type="primary"):
        save_list = []
        # Gác
        for g in final_gac:
            if g["HoTen"] != "N/A": save_list.append(g)
        # Tuần tra
        for p in tt1: save_list.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
        for p in tt2: save_list.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
        # Phát sinh
        if ps_name and ps_mem:
            for p in ps_mem: save_list.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_d})
        
        df_final = pd.DataFrame(save_list)
        df_final["Tuan"] = selected_week
        df_final["Ngay"] = selected_day
        df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y")
        
        try:
            updated = pd.concat([df_history, df_final], ignore_index=True)
            conn.update(worksheet="NhiemVu", data=updated)
            st.success("🎉 Đã lưu lịch phân công và cập nhật điểm thành công!")
            st.balloons()
        except:
            st.error("Lỗi: Không thể ghi dữ liệu lên Sheet 'NhiemVu'.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
