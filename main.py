import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "13579" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"] 

st.set_page_config(page_title="Hệ thống Điều hành ANTT", layout="wide")

# CSS tối ưu hiển thị
st.markdown("""
    <style>
    .report-box { background-color: #E0F2FE; padding: 15px; border-radius: 10px; border: 1px solid #0EA5E9; margin-bottom: 20px; }
    .duty-card { padding: 10px; border-radius: 8px; border-left: 5px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 8px; }
    .double-duty { background-color: #FFFBEB; border-left: 5px solid #F59E0B; }
    .name-tag { font-weight: bold; color: #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

try:
    # --- 2. KẾT NỐI DỮ LIỆU ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc Lịch trực gốc
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Đọc Lịch sử Nhiệm vụ (Sheet NhiemVu)
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. BỘ LỌC SIDEBAR ---
    st.sidebar.header("🔐 ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã xác thực:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # --- 4. GIAO DIỆN CHÍNH ---
    tab_view, tab_manage = st.tabs(["📋 BẢNG TRỰC & NHIỆM VỤ", "⚡ PHÂN CÔNG CHI TIẾT"])

    with tab_view:
        # A. HIỂN THỊ KẾT QUẢ ĐÃ PHÂN (ĐƯA LÊN ĐẦU)
        st.subheader("📌 NHIỆM VỤ CỤ THỂ HÔM NAY")
        saved_tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        
        if not saved_tasks.empty:
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            # Chuyển dữ liệu sang dạng bảng dễ nhìn
            st.dataframe(saved_tasks[["Gio", "HoTen", "LoaiNhiemVu"]].sort_values("Gio"), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Chưa có danh sách phân công chi tiết cho ngày này.")

        # B. DANH SÁCH QUÂN SỐ TRỰC (DƯỚI NHIỆM VỤ)
        st.subheader("👥 QUÂN SỐ TRỰC TẠI ĐƠN VỊ")
        c1, c2 = st.columns(2)
        morning_list = df_week[df_week[f"{d_code}_N"].str.contains('x', na=False)]['HoTen'].tolist()
        night_cax_list = df_week[df_week[f"{d_code}_D_CAX"].str.contains('x', na=False)]['HoTen'].tolist()
        night_ap_list = df_week[df_week[f"{d_code}_D_Ap"].str.contains('x', na=False)]['HoTen'].tolist()

        with c1:
            st.info("☀️ Trực Sáng")
            for n in morning_list:
                is_db = "double-duty" if (n in night_cax_list or n in night_ap_list) else ""
                st.markdown(f'<div class="duty-card {is_db}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)
        with c2:
            st.info("🌙 Trực Đêm")
            for n in night_cax_list:
                is_db = "double-duty" if n in morning_list else ""
                st.markdown(f'<div class="duty-card {is_db}"><span class="name-tag">{n} (Xã)</span></div>', unsafe_allow_html=True)
            for n in night_ap_list:
                st.markdown(f'<div class="duty-card"><span class="name-tag">{n} (Ấp)</span></div>', unsafe_allow_html=True)

    with tab_manage:
        if not is_admin:
            st.error("Vui lòng nhập mật mã điều hành để thực hiện thay đổi.")
            st.stop()

        # --- LOGIC GỢI Ý & TÍNH ĐIỂM ---
        # Tính tổng điểm tích lũy của từng người
        summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
        
        # Danh sách Nam (Sáng & Đêm Xã)
        pool_sang = pd.DataFrame({"HoTen": [n for n in morning_list if n not in LIST_NU]}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")
        pool_dem = pd.DataFrame({"HoTen": [n for n in night_cax_list if n not in LIST_NU]}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")

        # --- GIAO DIỆN CHỌN ---
        st.subheader("🛡️ PHÂN CA GÁC CỔNG")
        CA_GAC = [("07-10h", 1, "S"), ("10-13h", 1, "S"), ("13-15h", 1, "S"), ("15-17h", 1, "S"),
                  ("17-20h", 2, "D"), ("20-23h", 2, "D"), ("23-01h", 2, "D"), ("01-03h", 2, "D"), ("03-05h", 2, "D"), ("05-07h", 2, "D")]
        
        gac_data = []
        cg1, cg2 = st.columns(2)
        for i, (gio, d, loai) in enumerate(CA_GAC):
            p = pool_sang["HoTen"].tolist() if loai == "S" else pool_dem["HoTen"].tolist()
            with (cg1 if i < 5 else cg2):
                if p:
                    sel = st.selectbox(f"Ca {gio}", p, index=i%len(p), key=f"gac_{i}")
                    gac_data.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": d})

        st.divider()
        st.subheader("🚔 TUẦN TRA & PHÁT SINH")
        col_tt1, col_tt2 = st.columns(2)
        p_tt = pool_dem["HoTen"].tolist()
        with col_tt1:
            # Gợi ý tự động 4 người điểm thấp nhất cho ca 1
            tt1 = st.multiselect("Tuần tra C1 (18-22h):", p_tt, default=p_tt[:4] if len(p_tt)>=4 else p_tt)
        with col_tt2:
            # Gợi ý 4 người tiếp theo cho ca 2
            tt2 = st.multiselect("Tuần tra C2 (22-02h):", p_tt, default=p_tt[4:8] if len(p_tt)>=8 else [])
            
        ps_name = st.text_input("Nhiệm vụ đột xuất (Giữ đối tượng...):")
        ps_mem = st.multiselect("Đồng chí thực hiện (Cả Ấp & Xã):", df['HoTen'].unique().tolist())
        ps_diem = st.number_input("Chấm điểm thưởng:", 1, 10, 3)

        if st.button("💾 CẬP NHẬT LỊCH VÀ CỘNG ĐIỂM", use_container_width=True, type="primary"):
            # 1. Gom dữ liệu mới
            new_rows = []
            new_rows.extend(gac_data)
            for p in tt1: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
            for p in tt2: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
            if ps_name and ps_mem:
                for p in ps_mem: new_rows.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_diem})
            
            df_new = pd.DataFrame(new_rows)
            df_new["Tuan"] = selected_week
            df_new["Ngay"] = selected_day
            df_new["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

            # 2. XỬ LÝ CẬP NHẬT (Xóa cũ - Ghi mới)
            # Lọc bỏ những dòng thuộc tuần và ngày hiện tại trong lịch sử
            if not df_history.empty:
                df_history_cleaned = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                final_df = pd.concat([df_history_cleaned, df_new], ignore_index=True)
            else:
                final_df = df_new

            # 3. LƯU LẠI
            conn.update(worksheet="NhiemVu", data=final_df)
            st.success("✅ Đã cập nhật lịch thành công! Dữ liệu cũ đã được ghi đè.")
            st.balloons()

except Exception as e:
    st.error(f"Lỗi: {e}")
