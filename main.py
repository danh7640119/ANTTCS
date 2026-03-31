import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG ---
ADMIN_PASSWORD = "13579" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]

# ID Sắp xếp chuẩn theo thời gian (Bắt đầu từ 07h sáng)
GIO_ORDER = {
    "07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, 
    "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, 
    "03-05h": 9, "05-07h": 10
}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

st.markdown("""
    <style>
    .morning-card { padding: 10px; border-radius: 8px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 8px; }
    .night-cax-card { padding: 10px; border-radius: 8px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 8px; }
    .night-ap-card { padding: 10px; border-radius: 8px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 8px; }
    .double-duty-warning { background-color: #FEE2E2 !important; border: 2px solid #EF4444 !important; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 25px 0 15px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    # --- 2. KẾT NỐI DỮ LIỆU ---
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

    # --- 3. BỘ LỌC SIDEBAR ---
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    list_weeks = df['Tuan'].unique().tolist()[::-1]
    selected_week = st.sidebar.selectbox("Tuần trực:", list_weeks)
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_week = df[df['Tuan'] == selected_week]

    morning_list = df_week[df_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_week[df_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_week[df_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT"])

    with tab_view:
        st.subheader(f"📌 NHIỆM VỤ NGÀY {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        if not tasks.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.write("**🛡️ Gác Cổng (Theo ID ca)**")
                gac_view = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                gac_view['SortID'] = gac_view['Gio'].map(GIO_ORDER)
                st.table(gac_view.sort_values('SortID')[["Gio", "HoTen"]])
            with c2:
                st.write("**🚔 Tuần Tra & Khác**")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["Gio", "HoTen", "LoaiNhiemVu"]])
        else:
            st.info("Chưa có lịch trực chi tiết.")

    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập mật mã điều hành.")
        else:
            current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
            
            def get_sorted_pool(names):
                names_nam = [n for n in names if n not in LIST_NU]
                return pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0).sort_values("Diem")["HoTen"].tolist()

            pool_sang = get_sorted_pool(morning_list)
            pool_dem = get_sorted_pool(night_cax_list)

            # 1. GÁC CỔNG
            st.subheader("🛡️ ĐIỀU ĐỘNG GÁC CỔNG")
            gac_results = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(list(GIO_ORDER.keys())):
                p = pool_sang if i < 4 else pool_dem
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                default_idx = i % len(p) if p else 0
                if not saved.empty and saved.iloc[0]['HoTen'] in p:
                    default_idx = p.index(saved.iloc[0]['HoTen'])
                with (cg1 if i < 5 else cg2):
                    if p:
                        sel = st.selectbox(f"Ca {gio}", p, index=default_idx, key=f"gac_v10_{i}")
                        gac_results.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": (1 if i < 4 else 2)})

            # 2. TUẦN TRA (Đã khôi phục)
            st.divider()
            st.subheader("🚔 TUẦN TRA ĐÊM")
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist()
            if not def_tt1: def_tt1 = pool_dem[:4]
            if not def_tt2: def_tt2 = pool_dem[4:8]

            ct1, ct2 = st.columns(2)
            with ct1: tt1 = st.multiselect("Ca 1 (18-22h):", pool_dem, default=[x for x in def_tt1 if x in pool_dem])
            with ct2: tt2 = st.multiselect("Ca 2 (22-02h):", pool_dem, default=[x for x in def_tt2 if x in pool_dem])

            # 3. ĐỘT XUẤT (Đã khôi phục)
            st.subheader("🆘 ĐỘT XUẤT")
            saved_ps = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐỘT XUẤT", na=False)]
            ps_name = st.text_input("Tên việc:", value=saved_ps.iloc[0]['LoaiNhiemVu'].replace("ĐỘT XUẤT: ", "") if not saved_ps.empty else "")
            ps_mem = st.multiselect("Đồng chí thực hiện:", df['HoTen'].unique().tolist(), default=saved_ps['HoTen'].tolist() if not saved_ps.empty else [])
            ps_diem = st.number_input("Điểm thưởng:", 1, 15, 3)

            if st.button("💾 LƯU PHƯƠNG ÁN", use_container_width=True, type="primary"):
                new_rows = []
                new_rows.extend(gac_results)
                for p in tt1: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2})
                for p in tt2: new_rows.append({"HoTen": p, "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2})
                if ps_name and ps_mem:
                    for p in ps_mem: new_rows.append({"HoTen": p, "LoaiNhiemVu": f"ĐỘT XUẤT: {ps_name}", "Gio": "Đột xuất", "Diem": ps_diem})
                
                df_final = pd.DataFrame(new_rows)
                df_final["Tuan"], df_final["Ngay"] = selected_week, selected_day
                df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                if not df_history.empty:
                    df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                    final_save = pd.concat([df_history, df_final], ignore_index=True)
                else: final_save = df_final
                
                conn.update(worksheet="NhiemVu", data=final_save)
                st.success("Đã cập nhật lịch trực!")
                st.rerun()

    # --- 5. DANH SÁCH TỔNG (LUÔN HIỆN DƯỚI CÙNG) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    cs, cd, ca = st.columns(3)
    with cs:
        st.markdown("<p style='color: #2563EB; font-weight: bold; text-align: center;'>☀️ TRỰC SÁNG (XÃ)</p>", unsafe_allow_html=True)
        for n in morning_list:
            is_warn = "double-duty-warning" if n in night_cax_list else ""
            st.markdown(f'<div class="morning-card {is_warn}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)
    with cd:
        st.markdown("<p style='color: #EA580C; font-weight: bold; text-align: center;'>🌙 TRỰC ĐÊM (XÃ)</p>", unsafe_allow_html=True)
        for n in night_cax_list:
            is_warn = "double-duty-warning" if n in morning_list else ""
            st.markdown(f'<div class="night-cax-card {is_warn}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)
    with ca:
        st.markdown("<p style='color: #16A34A; font-weight: bold; text-align: center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list:
            st.markdown(f'<div class="night-ap-card"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
