import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS màu sắc & Cảnh báo (Giữ nguyên phong cách V11)
st.markdown("""
    <style>
    .dot-xuat-container { background-color: #FFF5F5; padding: 20px; border-radius: 10px; border: 2px dashed #FECACA; margin-top: 20px; }
    .morning-card { padding: 10px; border-radius: 8px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 8px; }
    .night-cax-card { padding: 10px; border-radius: 8px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 8px; }
    .night-ap-card { padding: 10px; border-radius: 8px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 8px; }
    .double-duty-warning { background-color: #FEE2E2 !important; border: 2px solid #EF4444 !important; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 25px 0 15px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    df_raw = conn.read(spreadsheet=url, worksheet="luutru", ttl=0, skiprows=2)
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df = df_raw.dropna(subset=['HoTen']).copy()

    try:
        df_history = conn.read(spreadsheet=url, worksheet="NhiemVu", ttl=0)
    except:
        df_history = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "LoaiNhiemVu", "Gio", "Diem", "NgayTao"])

    # Sidebar
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    selected_week = st.sidebar.selectbox("Tuần trực:", df['Tuan'].unique().tolist()[::-1])
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
                st.info("🛡️ Gác Cổng")
                gac_v = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                gac_v['SortID'] = gac_v['Gio'].map(GIO_ORDER)
                st.table(gac_v.sort_values('SortID')[["Gio", "HoTen"]])
            with c2:
                st.warning("🚔 Tuần Tra & Đột Xuất")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["LoaiNhiemVu", "HoTen", "Gio"]])
        else: st.info("Chưa có lịch trực chi tiết.")

    with tab_manage:
        if not is_admin:
            st.warning("Vui lòng nhập mật mã điều hành.")
        else:
            current_saved = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
            
            # --- LOGIC TÍNH ĐIỂM & TẠO DANH SÁCH CHỌN ---
            summary = df_history.groupby("HoTen")["Diem"].sum().reset_index() if not df_history.empty else pd.DataFrame(columns=["HoTen", "Diem"])
            
            def get_display_pool(names):
                # 1. Lọc nam và kết hợp điểm
                names_nam = [n for n in names if n not in LIST_NU]
                df_p = pd.DataFrame({"HoTen": names_nam}).merge(summary, on="HoTen", how="left").fillna(0)
                # 2. Sắp xếp điểm thấp lên đầu
                df_p = df_p.sort_values("Diem", ascending=True)
                # 3. Tạo chuỗi hiển thị: "Tên (Điểm)"
                df_p["Display"] = df_p.apply(lambda r: f"{r['HoTen']} ({int(r['Diem'])}đ)", axis=1)
                return df_p

            pool_s_df = get_display_pool(morning_list)
            pool_d_df = get_display_pool(night_cax_list)
            all_mem_df = get_display_pool(df['HoTen'].unique().tolist())

            # Map ngược từ Display về HoTen để lưu
            display_to_real = dict(zip(all_mem_df["Display"], all_mem_df["HoTen"]))

            # 1. GÁC CỔNG
            st.subheader("🛡️ ĐIỀU ĐỘNG GÁC CỔNG")
            gac_rows = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(list(GIO_ORDER.keys())):
                df_pool = pool_s_df if i < 4 else pool_d_df
                saved = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                
                # Tìm index của người đã lưu (nếu có)
                default_idx = i % len(df_pool) if not df_pool.empty else 0
                if not saved.empty:
                    real_name = saved.iloc[0]['HoTen']
                    match = df_pool[df_pool['HoTen'] == real_name]
                    if not match.empty:
                        default_idx = df_pool.index.get_loc(match.index[0])

                with (cg1 if i < 5 else cg2):
                    if not df_pool.empty:
                        sel_display = st.selectbox(f"Ca {gio}", df_pool["Display"], index=default_idx, key=f"gac_v12_{i}")
                        gac_rows.append({"HoTen": display_to_real[sel_display], "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": (1 if i < 4 else 2)})

            # 2. TUẦN TRA
            st.divider()
            st.subheader("🚔 TUẦN TRA ĐÊM")
            def_tt1 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C1']['HoTen'].tolist() or pool_d_df["HoTen"].head(4).tolist()
            def_tt2 = current_saved[current_saved['LoaiNhiemVu'] == 'Tuần tra C2']['HoTen'].tolist() or pool_d_df["HoTen"].iloc[4:8].tolist()
            
            ct1, ct2 = st.columns(2)
            with ct1: 
                tt1_disp = st.multiselect("Tuần tra C1 (18-22h):", pool_d_df["Display"], 
                                         default=[f"{n} ({int(summary[summary['HoTen']==n]['Diem'].sum())}đ)" for n in def_tt1 if n in pool_d_df["HoTen"].values])
            with ct2: 
                tt2_disp = st.multiselect("Tuần tra C2 (22-02h):", pool_d_df["Display"], 
                                         default=[f"{n} ({int(summary[summary['HoTen']==n]['Diem'].sum())}đ)" for n in def_tt2 if n in pool_d_df["HoTen"].values])

            # 3. ĐỘT XUẤT (DIV RIÊNG)
            st.markdown('<div class="dot-xuat-container">', unsafe_allow_html=True)
            st.subheader("🆘 NHIỆM VỤ ĐỘT XUẤT")
            if 'num_tasks' not in st.session_state: st.session_state.num_tasks = 1
            if st.button("➕ Thêm nhóm nhiệm vụ"): st.session_state.num_tasks += 1
            
            saved_dx = current_saved[current_saved['LoaiNhiemVu'].str.contains("ĐX: ", na=False)]
            unique_tasks = saved_dx['LoaiNhiemVu'].unique().tolist()
            dx_final_rows = []
            
            for i in range(max(st.session_state.num_tasks, len(unique_tasks))):
                st.write(f"--- Nhóm {i+1} ---")
                c_dx1, c_dx2, c_dx3 = st.columns([3, 5, 1])
                d_name = unique_tasks[i].replace("ĐX: ", "") if i < len(unique_tasks) else ""
                d_mem_real = saved_dx[saved_dx['LoaiNhiemVu'] == unique_tasks[i]]['HoTen'].tolist() if i < len(unique_tasks) else []
                
                with c_dx1: t_name = st.text_input(f"Việc {i+1}", value=d_name, key=f"dx_n_{i}")
                with c_dx2: t_mem_disp = st.multiselect(f"Đ/C {i+1}", all_mem_df["Display"], 
                                                      default=[f"{n} ({int(summary[summary['HoTen']==n]['Diem'].sum())}đ)" for n in d_mem_real if n in all_mem_df["HoTen"].values], key=f"dx_m_{i}")
                with c_dx3: t_diem = st.number_input(f"Điểm", 1, 10, 3, key=f"dx_d_{i}")
                
                if t_name and t_mem_disp:
                    for m_disp in t_mem_disp: dx_final_rows.append({"HoTen": display_to_real[m_disp], "LoaiNhiemVu": f"ĐX: {t_name}", "Gio": "Đột xuất", "Diem": t_diem})
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("💾 LƯU TOÀN BỘ PHƯƠNG ÁN", use_container_width=True, type="primary"):
                final_all = gac_rows + [{"HoTen": display_to_real[p], "LoaiNhiemVu": "Tuần tra C1", "Gio": "18-22h", "Diem": 2} for p in tt1_disp] + \
                            [{"HoTen": display_to_real[p], "LoaiNhiemVu": "Tuần tra C2", "Gio": "22-02h", "Diem": 2} for p in tt2_disp] + dx_final_rows
                df_s = pd.DataFrame(final_all)
                df_s["Tuan"], df_s["Ngay"], df_s["NgayTao"] = selected_week, selected_day, datetime.now().strftime("%d/%m/%Y %H:%M")
                
                if not df_history.empty:
                    df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                    final_save = pd.concat([df_history, df_s], ignore_index=True)
                else: final_save = df_s
                conn.update(worksheet="NhiemVu", data=final_save)
                st.success("Đã cập nhật điểm và lịch trực thành công!")
                st.rerun()

    # --- 6. DANH SÁCH TỔNG (DƯỚI CÙNG) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    cs, cd, ca = st.columns(3)
    with cs:
        st.markdown("<p style='color:#2563EB; font-weight:bold; text-align:center;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in morning_list: st.markdown(f'<div class="morning-card {"double-duty-warning" if n in night_cax_list else ""}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)
    with cd:
        st.markdown("<p style='color:#EA580C; font-weight:bold; text-align:center;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in night_cax_list: st.markdown(f'<div class="night-cax-card {"double-duty-warning" if n in morning_list else ""}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)
    with ca:
        st.markdown("<p style='color:#16A34A; font-weight:bold; text-align:center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list: st.markdown(f'<div class="night-ap-card"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)

except Exception as e: st.error(f"Lỗi: {e}")
