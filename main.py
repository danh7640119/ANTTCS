import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ thống Điều hành ANTT", layout="wide", page_icon="👮")

st.markdown("""
    <style>
    .time-box { background-color: #F3F4F6; padding: 12px; border-radius: 8px; border-left: 6px solid #1E3A8A; margin-bottom: 20px; font-weight: bold; color: #1E3A8A; }
    .duty-card { padding: 10px; border-radius: 10px; border-left: 5px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 8px; }
    .double-duty { background-color: #FFFBEB; border-left: 5px solid #F59E0B; }
    .name-text { color: #1E3A8A; font-size: 15px; font-weight: bold; }
    .group-header { background-color: #1E3A8A; color: white; padding: 10px; border-radius: 5px; margin: 15px 0; font-weight: bold; }
    .section-title { color: #1E3A8A; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- DANH SÁCH ĐỒNG CHÍ NỮ (Cập nhật tên chính xác tại đây) ---
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"] 

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu trực gốc
    df_raw = conn.read(spreadsheet=url, ttl=0, worksheet="1727254590", skiprows=2)
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
    st.sidebar.header("📅 THÔNG TIN TRỰC")
    selected_week = st.sidebar.selectbox("Chọn tuần:", list_weeks, index=default_week_idx)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Chọn ngày:", days_vn, index=now.weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # --- 4. HIỂN THỊ DANH SÁCH TRỰC BAN ĐẦU ---
    st.title("👮 HỆ THỐNG ĐIỀU HÀNH TÁC CHIẾN")
    st.markdown(f'<div class="time-box">📅 {selected_week} | {selected_day}</div>', unsafe_allow_html=True)
    
    tab_list, tab_assign = st.tabs(["📋 Danh sách trực hôm nay", "⚡ Phân công nhiệm vụ"])

    with tab_list:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="group-header">☀️ TRỰC BAN NGÀY</div>', unsafe_allow_html=True)
            morning_duty = df_week[df_week[f"{d_code}_N"] == 'x']
            for _, r in morning_duty.iterrows():
                st.markdown(f'<div class="duty-card"><div class="name-text">{r["HoTen"]} ({r["Ap"]})</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="group-header">🌙 TRỰC BAN ĐÊM (CAX)</div>', unsafe_allow_html=True)
            night_cax = df_week[df_week[f"{d_code}_D_CAX"] == 'x']
            for _, r in night_cax.iterrows():
                st.markdown(f'<div class="duty-card"><div class="name-text">{r["HoTen"]}</div></div>', unsafe_allow_html=True)

    with tab_assign:
        # --- 5. CHUẨN BỊ QUÂN SỐ PHÂN CÔNG ---
        # Lấy danh sách điểm tích lũy
        summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
        
        # Nhóm 1: Trực sáng (không tính nữ) -> Gác 7h-17h
        list_sang = [n for n in morning_duty['HoTen'].tolist() if n not in LIST_NU]
        df_sang = pd.DataFrame({"HoTen": list_sang}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
        
        # Nhóm 2: Trực đêm CAX (không tính nữ) -> Gác 17h-7h & Tuần tra
        list_dem_cax = [n for n in night_cax['HoTen'].tolist() if n not in LIST_NU]
        df_dem = pd.DataFrame({"HoTen": list_dem_cax}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
        
        # Nhóm 3: Toàn bộ quân số (bao gồm cả Ấp) -> Nhiệm vụ phát sinh
        list_all = df_week['HoTen'].tolist()

        # --- 6. PHÂN CÔNG GÁC CỔNG (10 CA) ---
        st.subheader("🛡️ PHÂN CA GÁC CỔNG (24H)")
        CA_GAC = [
            ("07:00-10:00", 1, "SANG"), ("10:00-13:00", 1, "SANG"), ("13:00-15:00", 1, "SANG"), ("15:00-17:00", 1, "SANG"),
            ("17:00-20:00", 2, "DEM"), ("20:00-23:00", 2, "DEM"), ("23:00-01:00", 2, "DEM"), ("01:00-03:00", 2, "DEM"), 
            ("03:00-05:00", 2, "DEM"), ("05:00-07:00", 2, "DEM")
        ]
        
        final_gac = []
        c_g1, c_g2 = st.columns(2)
        for i, (gio, diem, loai) in enumerate(CA_GAC):
            pool = df_sang["HoTen"].tolist() if loai == "SANG" else df_dem["HoTen"].tolist()
            with (c_g1 if i < 5 else c_g2):
                if not pool:
                    st.warning(f"Ca {gio}: Không có quân số!")
                    sel = "N/A"
                else:
                    sel = st.selectbox(f"Ca {gio} ({'Sáng' if loai=='SANG' else 'Đêm Xã'})", pool, index=i%len(pool), key=f"gac_{i}")
                final_gac.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": diem})

        # --- 7. PHÂN CÔNG TUẦN TRA ---
        st.markdown('<h3 class="section-title">🚔 TUẦN TRA ĐÊM (Lấy quân số trực Xã)</h3>', unsafe_allow_html=True)
        col_tt1, col_tt2 = st.columns(2)
        # Gợi ý sẵn 4 người ít điểm nhất cho ca 1, 4 người tiếp theo cho ca 2
        goi_y_tt = df_dem["HoTen"].tolist()
        
        with col_tt1:
            st.write("**Ca 1 (18h - 22h)**")
            tt1 = st.multiselect("Đ/c tuần tra C1:", goi_y_tt, default=goi_y_tt[:4] if len(goi_y_tt)>=4 else goi_y_tt)
        with col_tt2:
            st.write("**Ca 2 (22h - 02h)**")
            tt2 = st.multiselect("Đ/c tuần tra C2:", goi_y_tt, default=goi_y_tt[4:8] if len(goi_y_tt)>=8 else [])

        # --- 8. NHIỆM VỤ PHÁT SINH ---
        st.markdown('<h3 class="section-title">🆘 NHIỆM VỤ PHÁT SINH (Giữ đối tượng, đột xuất...)</h3>', unsafe_allow_html=True)
        c_ps1, c_ps2, c_ps3 = st.columns([2,1,1])
        with c_ps1: ps_name = st.text_input("Tên nhiệm vụ phát sinh:")
        with c_ps2: ps_mem = st.multiselect("Đồng chí thực hiện (Cả Ấp/Xã):", list_all)
        with c_ps3: ps_d = st.number_input("Chấm điểm:", 1, 10, 3)

        # --- 9. NÚT LƯU ---
        st.divider()
        if st.button("💾 XÁC NHẬN VÀ LƯU TOÀN BỘ PHÂN CÔNG", use_container_width=True, type="primary"):
            all_data = []
            # Gom Gác cổng
            for g in final_gac: 
                if g["HoTen"] != "N/A": all_data.append(g)
            # Gom Tuần tra
            for p in tt1: all_data.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
            for p in tt2: all_data.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
            # Gom Phát sinh
            if ps_name and ps_mem:
                for p in ps_mem: all_data.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_d})
            
            df_final = pd.DataFrame(all_data)
            df_final["Tuan"] = selected_week
            df_final["Ngay"] = selected_day
            df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y")
            
            try:
                updated = pd.concat([df_history, df_final], ignore_index=True)
                conn.update(worksheet="NhiemVu", data=updated)
                st.success("🎉 Đã cập nhật lịch trực và điểm tích lũy thành công!")
                st.balloons()
            except:
                st.error("Lỗi: Không thể ghi dữ liệu. Vui lòng kiểm tra Sheet 'NhiemVu'.")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
