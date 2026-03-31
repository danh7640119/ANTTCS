import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH ---
ADMIN_PASSWORD = "123" 
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]

# Khung giờ chuẩn để sắp xếp ID (Mapping)
GIO_ORDER = {
    "07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, 
    "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, 
    "03-05h": 9, "05-07h": 10
}

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# CSS màu sắc (Giữ nguyên logic V8)
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

    # --- 3. SIDEBAR & XỬ LÝ QUÂN SỐ ---
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

    # --- 4. GIAO DIỆN CHÍNH ---
    tab_view, tab_manage = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG CHI TIẾT"])

    with tab_view:
        st.subheader(f"📌 NHIỆM VỤ CÔNG TÁC NGÀY {selected_day}")
        tasks = df_history[(df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day)]
        
        if not tasks.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.write("**🛡️ Lịch Gác Cổng**")
                gac_view = tasks[tasks['LoaiNhiemVu'] == 'Gác cổng'].copy()
                # TẠO ID SẮP XẾP: Ánh xạ cột Gio qua bảng GIO_ORDER để lấy STT chuẩn
                gac_view['SortID'] = gac_view['Gio'].map(GIO_ORDER)
                gac_view = gac_view.sort_values('SortID')
                st.table(gac_view[["Gio", "HoTen"]]) # Không hiện cột ID, chỉ dùng để sắp xếp
                
            with c2:
                st.write("**🚔 Tuần Tra & Khác**")
                st.table(tasks[tasks['LoaiNhiemVu'] != 'Gác cổng'][["Gio", "HoTen", "LoaiNhiemVu"]])
        else:
            st.info("Chưa có lịch phân công chi tiết.")

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

            st.subheader("🛡️ ĐIỀU ĐỘNG GÁC CỔNG (Sắp xếp theo tiến trình thời gian)")
            # Danh sách ca để Loop tạo Selectbox
            CA_LIST = list(GIO_ORDER.keys())
            
            gac_results = []
            cg1, cg2 = st.columns(2)
            for i, gio in enumerate(CA_LIST):
                # Xác định điểm và loại (Sáng/Đêm) dựa trên ca
                diem = 1 if i < 4 else 2
                loai = "S" if i < 4 else "D"
                p = pool_sang if loai == "S" else pool_dem
                
                # Check dữ liệu cũ
                saved_person = current_saved[(current_saved['Gio'] == gio) & (current_saved['LoaiNhiemVu'] == 'Gác cổng')]
                default_idx = i % len(p) if p else 0
                if not saved_person.empty and saved_person.iloc[0]['HoTen'] in p:
                    default_idx = p.index(saved_person.iloc[0]['HoTen'])

                with (cg1 if i < 5 else cg2):
                    if p:
                        sel = st.selectbox(f"Ca trực {gio}", p, index=default_idx, key=f"gac_v9_{i}")
                        gac_results.append({"HoTen": sel, "LoaiNhiemVu": "Gác cổng", "Gio": gio, "Diem": diem})

            if st.button("💾 CẬP NHẬT PHƯƠNG ÁN", use_container_width=True, type="primary"):
                # Gom dữ liệu (Tương tự V8 nhưng đảm bảo Gio lưu vào Sheet chuẩn format)
                new_rows = []
                new_rows.extend(gac_results)
                # ... (Thêm phần tuần tra vào đây tương tự bản cũ)
                df_final = pd.DataFrame(new_rows)
                df_final["Tuan"], df_final["Ngay"] = selected_week, selected_day
                df_final["NgayTao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                if not df_history.empty:
                    df_history = df_history[~((df_history['Tuan'] == selected_week) & (df_history['Ngay'] == selected_day))]
                    final_save = pd.concat([df_history, df_final], ignore_index=True)
                else: final_save = df_final
                
                conn.update(worksheet="NhiemVu", data=final_save)
                st.success("Đã cập nhật lịch trực thành công!")
                st.rerun()

    # --- 5. DANH SÁCH TỔNG VỚI LOGIC TÔ MÀU CHÍNH XÁC ---
    st.markdown('<div class="section-header">👥 DANH SÁCH QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    cs, cd, ca = st.columns(3)
    
    with cs:
        st.markdown("<p style='color: #2563EB; font-weight: bold; text-align: center;'>☀️ TRỰC SÁNG (XÃ)</p>", unsafe_allow_html=True)
        for n in morning_list:
            # Nếu trực Sáng Xã mà cũng trực Đêm Xã -> Cảnh báo
            is_warn = "double-duty-warning" if n in night_cax_list else ""
            st.markdown(f'<div class="morning-card {is_warn}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)

    with cd:
        st.markdown("<p style='color: #EA580C; font-weight: bold; text-align: center;'>🌙 TRỰC ĐÊM (XÃ)</p>", unsafe_allow_html=True)
        for n in night_cax_list:
            # Nếu trực Đêm Xã mà cũng trực Sáng Xã -> Cảnh báo
            is_warn = "double-duty-warning" if n in morning_list else ""
            st.markdown(f'<div class="night-cax-card {is_warn}"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)

    with ca:
        st.markdown("<p style='color: #16A34A; font-weight: bold; text-align: center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list:
            st.markdown(f'<div class="night-ap-card"><span class="name-tag">{n}</span></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
