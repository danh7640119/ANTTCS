import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

try:
    # --- 2. KẾT NỐI DỮ LIỆU ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Load bảng trực gốc
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes:
        cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    # Load lịch sử nhiệm vụ
    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # --- 3. SIDEBAR ---
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần trực:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    # Lấy danh sách quân số trực thực tế ngày hôm đó
    morning_list = df_week[df_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_week[df_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage = st.tabs(["📋 BẢNG NHIỆM VỤ", "⚙️ ĐIỀU ĐỘNG"])

    with tab_view:
        # (Phần hiển thị Tab View giữ nguyên như bản V5)
        st.subheader(f"📌 NHIỆM VỤ NGÀY {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            c1, c2 = st.columns(2)
            with c1: st.table(tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'][["Gio", "HoTen"]].sort_values("Gio"))
            with c2: st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["Gio", "HoTen", "LoaiNhiemVu"]])
        else:
            st.warning("Chưa phân công chi tiết.")

    with tab_manage:
        if not is_admin:
            st.error("Nhập mã để phân công.")
            st.stop()

        # --- LOGIC QUAN TRỌNG: KIỂM TRA DỮ LIỆU ĐÃ LƯU ---
        current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        
        # Tính điểm tích lũy để gợi ý (nếu chưa có lịch lưu)
        summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
        
        def get_sorted_pool(names):
            names_nam = [n for n in names if n not in LIST_NU]
            return pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")["HoTen"].tolist()

        pool_sang = get_sorted_pool(morning_list)
        pool_dem = get_sorted_pool(night_cax_list)

        # 1. PHÂN CA GÁC CỔNG
        st.subheader("🛡️ GÁC CỔNG")
        CA_GAC = [("07-10h", 1, "S"), ("10-13h", 1, "S"), ("13-15h", 1, "S"), ("15-17h", 1, "S"),
                  ("17-20h", 2, "D"), ("20-23h", 2, "D"), ("23-01h", 2, "D"), ("01-03h", 2, "D"), ("03-05h", 2, "D"), ("05-07h", 2, "D")]
        
        gac_results = []
        cg1, cg2 = st.columns(2)
        for i, (gio, d, loai) in enumerate(CA_GAC):
            p = pool_sang if loai == "S" else pool_dem
            # KIỂM TRA: Nếu trong db đã có người gác ca này, lấy người đó làm default
            saved_person = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
            
            default_idx = i % len(p) if p else 0
            if not saved_person.empty:
                val = saved_person.iloc[0]['HoTen']
                if val in p: default_idx = p.index(val)

            with (cg1 if i < 5 else cg2):
                if p:
                    sel = st.selectbox(f"Ca {gio}", p, index=default_idx, key=f"gac_{selected_week}_{selected_day}_{i}")
                    gac_results.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": d})

        # 2. TUẦN TRA
        st.divider()
        st.subheader("🚔 TUẦN TRA")
        # Lấy default từ dữ liệu đã lưu
        def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
        def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
        
        # Nếu chưa có lưu thì mới dùng gợi ý 4 người đầu
        if not def_tt1: def_tt1 = pool_dem[:4] if len(pool_dem) >= 4 else []
        if not def_tt2: def_tt2 = pool_dem[4:8] if len(pool_dem) >= 8 else []

        ct1, ct2 = st.columns(2)
        with ct1: tt1 = st.multiselect("Ca 1 (18-22h):", pool_dem, default=[x for x in def_tt1 if x in pool_dem])
        with ct2: tt2 = st.multiselect("Ca 2 (22-02h):", pool_dem, default=[x for x in def_tt2 if x in pool_dem])

        # 3. PHÁT SINH (Chỉ hiện lại tên việc đã lưu nếu có)
        st.subheader("🆘 ĐỘT XUẤT")
        saved_ps = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐỘT XUẤT", na=False)]
        def_ps_name = saved_ps.iloc[0]['LoaiNhiemVu'].replace("ĐỘT XUẤT: ", "") if not saved_ps.empty else ""
        def_ps_mem = saved_ps['HoTen'].tolist() if not saved_ps.empty else []
        
        ps_name = st.text_input("Tên việc:", value=def_ps_name)
        ps_mem = st.multiselect("Đồng chí thực hiện:", df['HoTen'].unique().tolist(), default=def_ps_mem)
        ps_diem = st.number_input("Điểm thưởng:", 1, 15, 3)

        if st.button("💾 CẬP NHẬT PHƯƠNG ÁN", use_container_width=True, type="primary"):
            # (Phần xử lý lưu giữ nguyên như bản V5)
            new_rows = []
            new_rows.extend(gac_results)
            for p in tt1: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
            for p in tt2: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
            if ps_name and ps_mem:
                for p in ps_mem: new_rows.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_diem})
            
            df_new = pd.DataFrame(new_rows)
            df_new["Tuan"] = selected_week
            df_new["Ngay"] = selected_day
            df_new["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

            if not df_history.empty:
                df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                final_save = pd.concat([df_history, df_new], ignore_index=True)
            else:
                final_save = df_new

            conn.update(worksheet="NhiemVu", data=final_save)
            st.success("✅ Đã cập nhật thành công!")
            st.rerun() # Tự động load lại để thấy dữ liệu mới

except Exception as e:
    st.error(f"Lỗi: {e}")
