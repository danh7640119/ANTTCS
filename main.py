import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CẤU HÌNH & SECRETS ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
    URL_SHEET = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("⚠️ LỖI CẤU HÌNH: Kiểm tra lại Streamlit Secrets!")
    st.stop()

# Danh sách nữ và TTL 2 phút
LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
TTL_TIME = "2m" 

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Đọc dữ liệu thô (Cache 2 phút để không bị chặn API)
    df_raw = conn.read(spreadsheet=URL_SHEET, worksheet="luutru", ttl=TTL_TIME, skiprows=2)
    
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Sidebar điều hướng
    st.sidebar.header("🔐 HỆ THỐNG ĐIỀU HÀNH")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    # Lấy danh sách trực từ sheet luutru
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "✅ ĐIỂM DANH"])

    # --- TAB 1: XEM NHIỆM VỤ (Công khai hoặc theo ý đồng chí) ---
    with tab_view:
        st.subheader(f"📌 LỊCH TRỰC {selected_day} - TUẦN {selected_week}")
        # Hiển thị quân số trực tổng quan (Morning/Night/Ap) ở đây...

    # --- TAB 2: PHÂN CÔNG (ĐÃ KHÓA) ---
    with tab_manage:
        if not is_admin:
            st.warning("⚠️ Vui lòng nhập Mã điều hành để thực hiện phân công.")
        else:
            st.success("🔓 Đã xác thực quyền Điều hành.")
            # Logic phân công chi tiết của đồng chí...

    # --- TAB 3: ĐIỂM DANH (ĐÃ KHÓA GIỐNG TAB NHIỆM VỤ) ---
    with tab_attendance:
        if not is_admin:
            st.warning("⚠️ Quyền truy cập bị hạn chế. Vui lòng nhập Mã điều hành ở thanh bên để điểm danh.")
        else:
            st.subheader(f"✅ ĐIỂM DANH QUÂN SỐ - {selected_day}")
            
            # Gom danh sách tổng hợp
            all_direct = []
            for n in morning_list: all_direct.append({"HoTen": n, "Loai": "Sáng"})
            for n in night_cax_list: all_direct.append({"HoTen": n, "Loai": "Đêm Xã"})
            for n in night_ap_list: all_direct.append({"HoTen": n, "Loai": "Đêm Ấp"})
            
            df_att_input = pd.DataFrame(all_direct).drop_duplicates(subset=['HoTen'])

            if df_att_input.empty:
                st.info("Không có danh sách trực trong ngày này.")
            else:
                att_results = []
                # Dùng form để tránh việc nhảy trang mỗi lần tích chọn
                with st.form("attendance_form"):
                    for _, row in df_att_input.iterrows():
                        c1, c2, c3 = st.columns([3, 3, 4])
                        c1.markdown(f"**{row['HoTen']}** ({row['Loai']})")
                        status = c2.radio("Trạng thái", ["Có mặt", "Vắng"], key=f"s_{row['HoTen']}", horizontal=True, label_visibility="collapsed")
                        reason = c3.text_input("Lý do", key=f"r_{row['HoTen']}", placeholder="Lý do vắng...", label_visibility="collapsed")
                        
                        att_results.append({
                            "Tuan": selected_week,
                            "Ngay": selected_day,
                            "HoTen": row['HoTen'],
                            "TrangThai": status,
                            "LyDo": reason if status == "Vắng" else "",
                            "LoaiTruc": row['Loai'],
                            "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                    
                    submitted = st.form_submit_button("💾 XÁC NHẬN & LƯU BẢNG ĐIỂM DANH", use_container_width=True)
                    
                    if submitted:
                        try:
                            # Đọc dữ liệu cũ để nối thêm (TTL=0 để đảm bảo data mới nhất khi ghi)
                            try:
                                df_db = conn.read(spreadsheet=URL_SHEET, worksheet="DiemDanh", ttl=0)
                            except:
                                df_db = pd.DataFrame(columns=["Tuan", "Ngay", "HoTen", "TrangThai", "LyDo", "LoaiTruc", "NgayTao"])
                            
                            df_new = pd.DataFrame(att_results)
                            df_final = pd.concat([df_db, df_new], ignore_index=True)
                            
                            conn.update(worksheet="DiemDanh", data=df_final)
                            st.success(f"Đã lưu điểm danh cho {len(att_results)} đồng chí!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Lỗi khi gửi dữ liệu lên Google Sheet: {e}")

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
