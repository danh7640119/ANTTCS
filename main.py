import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS để giao diện đồng bộ
st.markdown("""
    <style>
    .duty-card { padding: 10px; border-radius: 8px; border-left: 5px solid #1E3A8A; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 8px; }
    .double-duty { background-color: #FFFBEB; border-left: 5px solid #F59E0B; }
    .name-tag { font-weight: bold; color: #1E3A8A; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 25px 0 15px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    # --- 2. KẾT NỐI DỮ LIỆU (LUÔN CHẠY) ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. SIDEBAR & BIẾN DÙNG CHUNG ---
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần trực:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # Lấy danh sách quân số trực từ bảng luutru (Dùng chung cho cả 2 Tab)
    morning_list = df_week[df_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_week[df_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_week[df_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    # --- 4. GIAO DIỆN CHÍNH ---
    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT"])

    # --- TAB XEM ---
    with tab_view:
        st.subheader(f"📌 NHIỆM VỤ CỤ THỂ NGÀY {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            c1, c2 = st.columns(2)
            with c1: 
                st.write("**🛡️ Gác Cổng**")
                st.table(tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'][["Gio", "HoTen"]].sort_values("Gio"))
            with c2: 
                st.write("**🚔 Tuần Tra & Khác**")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["Gio", "HoTen", "LoaiNhiemVu"]])
        else:
            st.info("Ngày này chưa được phân công chi tiết nhiệm vụ.")

    # --- TAB PHÂN CÔNG ---
    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập mật mã tại Sidebar để thực hiện điều động quân số.")
        else:
            # Logic Load lại lịch cũ và Gợi ý (Kết hợp cả 2 như bạn yêu cầu)
            current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
            
            def get_sorted_pool(names):
                names_nam = [n for n in names if n not in LIST_NU]
                return pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")["HoTen"].tolist()

            pool_sang = get_sorted_pool(morning_list)
            pool_dem = get_sorted_pool(night_cax_list)

            st.subheader("🛡️ ĐIỀU ĐỘNG GÁC CỔNG")
            CA_GAC = [("07-10h", 1, "S"), ("10-13h", 1, "S"), ("13-15h", 1, "S"), ("15-17h", 1, "S"),
                      ("17-20h", 2, "D"), ("20-23h", 2, "D"), ("23-01h", 2, "D"), ("01-03h", 2, "D"), ("03-05h", 2, "D"), ("05-07h", 2, "D")]
            
            gac_results = []
            cg1, cg2 = st.columns(2)
            for i, (gio, d, loai) in enumerate(CA_GAC):
                p = pool_sang if loai == "S" else pool_dem
                # Kiểm tra lịch cũ
                saved_person = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                default_idx = i % len(p) if p else 0
                if not saved_person.empty and saved_person.iloc[0]['HoTen'] in p:
                    default_idx = p.index(saved_person.iloc[0]['HoTen'])

                with (cg1 if i < 5 else cg2):
                    if p:
                        sel = st.selectbox(f"Ca {gio}", p, index=default_idx, key=f"gac_{i}")
                        gac_results.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": d})

            st.divider()
            st.subheader("🚔 TUẦN TRA ĐÊM")
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
            if not def_tt1: def_tt1 = pool_dem[:4] if len(pool_dem) >= 4 else []
            if not def_tt2: def_tt2 = pool_dem[4:8] if len(pool_dem) >= 8 else []

            ct1, ct2 = st.columns(2)
            with ct1: tt1 = st.multiselect("Ca 1 (18-22h):", pool_dem, default=[x for x in def_tt1 if x in pool_dem])
            with ct2: tt2 = st.multiselect("Ca 2 (22-02h):", pool_dem, default=[x for x in def_tt2 if x in pool_dem])

            if st.button("💾 CẬP NHẬT PHƯƠNG ÁN", use_container_width=True, type="primary"):
                new_rows = []
                new_rows.extend(gac_results)
                for p in tt1: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
                for p in tt2: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
                
                df_final = pd.DataFrame(new_rows)
                df_final["Tuan"], df_final["Ngay"] = selected_week, selected_day
                df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

                if not df_history.empty:
                    df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                    final_save = pd.concat([df_history, df_final], ignore_index=True)
                else:
                    final_save = df_final

                conn.update(worksheet="NhiemVu", data=final_save)
                st.success("Đã cập nhật lịch thành công!")
                st.rerun()

    # --- 5. DANH SÁCH TRỰC TỔNG THỂ (LUÔN HIỆN Ở DƯỚI CÙNG) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN (Theo bảng luutru)</div>', unsafe_allow_html=True)
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

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
