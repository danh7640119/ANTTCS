import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
ADMIN_PASSWORD = "123" 
# Danh sách nữ đã cập nhật theo yêu cầu của bạn
LIST_NU = [
    "Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", 
    "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"
]

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

st.markdown("""
    <style>
    .task-card { background-color: #F0F9FF; padding: 15px; border-radius: 10px; border: 1px solid #BAE6FD; margin-bottom: 15px; }
    .duty-card { padding: 10px; border-radius: 8px; border-left: 5px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 8px; }
    .double-duty { background-color: #FFFBEB; border-left: 5px solid #F59E0B; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0 10px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    # --- 2. KẾT NỐI & TẢI DỮ LIỆU ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đã đổi tên worksheet thành "luutru" theo yêu cầu
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Đọc lịch sử nhiệm vụ và điểm số
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. BỘ LỌC SIDEBAR ---
    st.sidebar.header("🔐 QUẢN TRỊ VIÊN")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần trực:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # --- 4. GIAO DIỆN TAB ---
    tab_view, tab_manage = st.tabs(["📋 BẢNG NHIỆM VỤ CHI TIẾT", "⚙️ ĐIỀU ĐỘNG & PHÂN CÔNG"])

    with tab_view:
        st.markdown(f'<div class="section-header">📌 NHIỆM VỤ CÔNG TÁC NGÀY {selected_day} ({selected_week})</div>', unsafe_allow_html=True)
        
        # Lấy dữ liệu nhiệm vụ đã lưu
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        
        if not tasks.empty:
            c_view1, c_view2 = st.columns(2)
            with c_view1:
                st.subheader("🛡️ Lịch Gác Cổng")
                gac_table = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'][["Gio", "HoTen"]].sort_values("Gio")
                st.table(gac_table)
            with c_view2:
                st.subheader("🚔 Tuần tra & Đột xuất")
                other_table = tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["Gio", "HoTen", "LoaiNhiemVu"]]
                st.table(other_table)
        else:
            st.warning("⚠️ Chỉ huy chưa phân công nhiệm vụ chi tiết cho ngày này.")

        st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC BAN (TỔNG THỂ)</div>', unsafe_allow_html=True)
        morning_list = df_week[df_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        night_cax_list = df_week[df_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
        night_ap_list = df_week[df_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

        cv1, cv2 = st.columns(2)
        with cv1:
            st.info("☀️ Trực Sáng")
            for n in morning_list:
                is_db = "double-duty" if (n in night_cax_list or n in night_ap_list) else ""
                st.markdown(f'<div class="duty-card {is_db}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)
        with cv2:
            st.info("🌙 Trực Đêm")
            for n in night_cax_list:
                is_db = "double-duty" if n in morning_list else ""
                st.markdown(f'<div class="duty-card {is_db}"><span class="name-tag">{n} (Xã)</span></div>', unsafe_allow_html=True)
            for n in night_ap_list:
                st.markdown(f'<div class="duty-card"><span class="name-tag">{n} (Ấp)</span></div>', unsafe_allow_html=True)

    with tab_manage:
        if not is_admin:
            st.error("🔒 Vui lòng nhập đúng mã xác thực điều hành tại Sidebar để mở khóa tính năng này.")
            st.stop()

        # LOGIC TÍNH ĐIỂM & GỢI Ý
        summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
        
        def get_sorted_list(names):
            # Loại trừ nữ và sắp xếp người ít điểm lên đầu
            names_nam = [n for n in names if n not in LIST_NU]
            df_prio = pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
            return df_prio["HoTen"].tolist()

        pool_sang = get_sorted_list(morning_list)
        pool_dem = get_sorted_list(night_cax_list)

        st.subheader("🛡️ PHÂN CA GÁC CỔNG 24H")
        CA_GAC = [("07-10h", 1, "S"), ("10-13h", 1, "S"), ("13-15h", 1, "S"), ("15-17h", 1, "S"),
                  ("17-20h", 2, "D"), ("20-23h", 2, "D"), ("23-01h", 2, "D"), ("01-03h", 2, "D"), ("03-05h", 2, "D"), ("05-07h", 2, "D")]
        
        final_gac = []
        cg1, cg2 = st.columns(2)
        for i, (gio, d, loai) in enumerate(CA_GAC):
            p = pool_sang if loai == "S" else pool_dem
            with (cg1 if i < 5 else cg2):
                if p:
                    # Gợi ý mặc định theo điểm nhưng cho phép đổi sang bất kỳ ai trong list trực
                    sel = st.selectbox(f"Ca {gio}", p, index=i%len(p), key=f"gac_sel_{i}")
                    final_gac.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": d})

        st.divider()
        st.subheader("🚔 TUẦN TRA ĐÊM & PHÁT SINH")
        ct1, ct2 = st.columns(2)
        with ct1:
            tt1 = st.multiselect("Tuần tra C1 (18-22h):", pool_dem, default=pool_dem[:4] if len(pool_dem)>=4 else [])
        with ct2:
            tt2 = st.multiselect("Tuần tra C2 (22-02h):", pool_dem, default=pool_dem[4:8] if len(pool_dem)>=8 else [])
            
        st.write("**Nhiệm vụ đột xuất (Ghi điểm thưởng)**")
        c_ps1, c_ps2 = st.columns([3, 1])
        with c_ps1: ps_name = st.text_input("Tên việc (VD: Giữ đối tượng, Bảo vệ hiện trường...):")
        with c_ps1: ps_mem = st.multiselect("Đồng chí thực hiện:", df['HoTen'].unique().tolist())
        with c_ps2: ps_diem = st.number_input("Điểm thưởng:", 1, 15, 3)

        if st.button("💾 XÁC NHẬN CẬP NHẬT PHƯƠNG ÁN", use_container_width=True, type="primary"):
            # Tập hợp dữ liệu mới
            new_rows = []
            new_rows.extend(final_gac)
            for p in tt1: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
            for p in tt2: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
            if ps_name and ps_mem:
                for p in ps_mem: new_rows.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_diem})
            
            df_new = pd.DataFrame(new_rows)
            df_new["Tuan"] = selected_week
            df_new["Ngay"] = selected_day
            df_new["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

            # Logic Cập nhật: Xóa bản ghi cũ cùng ngày - lưu bản ghi mới
            if not df_history.empty:
                # Loại bỏ những dòng cũ của đúng ngày/tuần đó
                df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                final_save = pd.concat([df_history, df_new], ignore_index=True)
            else:
                final_save = df_new

            conn.update(worksheet="NhiemVu", data=final_save)
            st.success("🎉 Đã cập nhật phương án và cộng dồn điểm thành công!")
            st.balloons()

except Exception as e:
    st.error(f"Lỗi: {e}")
