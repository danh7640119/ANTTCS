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

LIST_NU = ["Ngô Thị Hồng Thắm", "Nguyễn Thị Thanh Tuyền", "Trần Thị Lan Phương", "Huỳnh Thị Thanh Nhi", "Đinh Thị Mai Quyền", "Vũ Thị Thơm"]
GIO_ORDER = {"07-10h": 1, "10-13h": 2, "13-15h": 3, "15-17h": 4, "17-20h": 5, "20-23h": 6, "23-01h": 7, "01-03h": 8, "03-05h": 9, "05-07h": 10}
TTL_2MIN = "2m" 

st.set_page_config(page_title="Điều hành ANTT Bắc Tân Uyên", layout="wide")

# --- 2. CSS GIAO DIỆN (KHÔI PHỤC MÀU SẮC) ---
st.markdown("""
    <style>
    .morning-card { padding: 10px; border-radius: 5px; border-left: 5px solid #2563EB; background-color: #EFF6FF; margin-bottom: 8px; }
    .morning-night-card { padding: 10px; border-radius: 5px; border-left: 5px solid #F59E0B; background-color: #FEF3C7; margin-bottom: 8px; }
    .night-cax-card { padding: 10px; border-radius: 5px; border-left: 5px solid #EA580C; background-color: #FFF7ED; margin-bottom: 8px; }
    .night-ap-card { padding: 10px; border-radius: 5px; border-left: 5px solid #16A34A; background-color: #F0FDF4; margin-bottom: 8px; }
    .name-tag { font-weight: bold; color: #1E3A8A; font-size: 15px; }
    .ap-tag { color: #64748B; font-size: 12px; font-style: italic; }
    .section-header { color: #1E3A8A; font-weight: bold; border-bottom: 2px solid #1E3A8A; padding-bottom: 5px; margin: 20px 0; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=URL_SHEET, worksheet="luutru", ttl=TTL_2MIN, skiprows=2)
    
    cols = ["Tuan", "Ap", "HoTen"]
    day_codes = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    for code in day_codes: cols.extend([f"{code}_N", f"{code}_D_CAX", f"{code}_D_Ap"])
    df_raw.columns = cols[:len(df_raw.columns)]
    df_mem = df_raw.dropna(subset=['HoTen']).copy()
    dict_ap = dict(zip(df_mem['HoTen'], df_mem['Ap']))

    # Sidebar
    st.sidebar.header("🔐 QUẢN TRỊ")
    access_key = st.sidebar.text_input("Mã điều hành:", type="password")
    is_admin = (access_key == ADMIN_PASSWORD)
    
    selected_week = st.sidebar.selectbox("Tuần trực:", df_mem['Tuan'].unique().tolist()[::-1])
    days_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    selected_day = st.sidebar.selectbox("Ngày trực:", days_vn, index=datetime.now().weekday())
    
    d_code = dict(zip(days_vn, day_codes))[selected_day]
    df_curr_week = df_mem[df_mem['Tuan'] == selected_week]
    
    morning_list = df_curr_week[df_curr_week[f"{d_code}_N"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_cax_list = df_curr_week[df_curr_week[f"{d_code}_D_CAX"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()
    night_ap_list = df_curr_week[df_curr_week[f"{d_code}_D_Ap"].astype(str).str.lower().str.contains('x', na=False)]['HoTen'].tolist()

    tab_view, tab_manage, tab_attendance = st.tabs(["📋 XEM NHIỆM VỤ", "⚙️ PHÂN CÔNG", "✅ ĐIỂM DANH"])

    # --- TAB XEM NHIỆM VỤ ---
    with tab_view:
        # (Phần này hiển thị bảng Gác cổng và Tuần tra như cũ của đồng chí)
        st.subheader(f"📌 LỊCH PHÂN CÔNG {selected_day}")

    # --- TAB PHÂN CÔNG (KHÓA) ---
    with tab_manage:
        if not is_admin: st.warning("Vui lòng nhập Mã điều hành.")
        else: st.write("Chức năng điều động quân số...")

    # --- TAB ĐIỂM DANH (CHỈ LƯU NGƯỜI VẮNG) ---
    with tab_attendance:
        if not is_admin:
            st.warning("Vui lòng nhập Mã điều hành để điểm danh.")
        else:
            st.subheader("✅ ĐIỂM DANH (Chỉ lưu danh sách vắng)")
            all_names = sorted(list(set(morning_list + night_cax_list + night_ap_list)))
            
            with st.form("form_attendance"):
                final_results = []
                for name in all_names:
                    c1, c2, c3 = st.columns([3, 3, 4])
                    c1.write(f"**{name}**")
                    status = c2.radio("Trạng thái", ["Có mặt", "Vắng"], key=f"att_{name}", horizontal=True, label_visibility="collapsed")
                    reason = c3.text_input("Lý do vắng", key=f"res_{name}", label_visibility="collapsed")
                    
                    if status == "Vắng":
                        # Xác định loại trực để lưu
                        loai = []
                        if name in morning_list: loai.append("Sáng")
                        if name in night_cax_list: loai.append("Đêm Xã")
                        if name in night_ap_list: loai.append("Đêm Ấp")
                        
                        final_results.append({
                            "Tuan": selected_week, "Ngay": selected_day, "HoTen": name,
                            "TrangThai": "Vắng", "LyDo": reason, "LoaiTruc": ", ".join(loai),
                            "NgayTao": datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                
                if st.form_submit_button("💾 XÁC NHẬN VÀ LƯU DANH SÁCH VẮNG"):
                    if not final_results:
                        st.success("Tất cả đều có mặt! Không có dữ liệu cần lưu.")
                    else:
                        try:
                            df_db = conn.read(spreadsheet=URL_SHEET, worksheet="DiemDanh", ttl=0)
                            df_final = pd.concat([df_db, pd.DataFrame(final_results)], ignore_index=True)
                            conn.update(worksheet="DiemDanh", data=df_final)
                            st.success(f"Đã ghi nhận {len(final_results)} trường hợp vắng.")
                        except:
                            st.error("Lỗi kết nối bảng DiemDanh.")

    # --- QUÂN SỐ TỔNG QUAN (PHÂN BIỆT MÀU SẮC) ---
    st.markdown('<div class="section-header">👥 QUÂN SỐ TRỰC TỔNG QUAN</div>', unsafe_allow_html=True)
    c_s, c_d, c_a = st.columns(3)
    
    with c_s:
        st.markdown("<p style='color:#2563EB; font-weight:bold; text-align:center;'>☀️ TRỰC SÁNG</p>", unsafe_allow_html=True)
        for n in morning_list:
            # KIỂM TRA XEM CÓ TRỰC ĐÊM XÃ KHÔNG ĐỂ ĐỔI MÀU
            is_night_cax = n in night_cax_list
            card_class = "morning-night-card" if is_night_cax else "morning-card"
            icon = " 🌙" if is_night_cax else ""
            st.markdown(f'''
                <div class="{card_class}">
                    <div class="name-tag">{n}{icon}</div>
                    <div class="ap-tag">Ấp: {dict_ap.get(n)}</div>
                </div>
            ''', unsafe_allow_html=True)
            
    with c_d:
        st.markdown("<p style='color:#EA580C; font-weight:bold; text-align:center;'>🌙 TRỰC ĐÊM XÃ</p>", unsafe_allow_html=True)
        for n in night_cax_list:
            st.markdown(f'''
                <div class="night-cax-card">
                    <div class="name-tag">{n}</div>
                    <div class="ap-tag">Ấp: {dict_ap.get(n)}</div>
                </div>
            ''', unsafe_allow_html=True)
            
    with c_a:
        st.markdown("<p style='color:#16A34A; font-weight:bold; text-align:center;'>🏡 TRỰC ẤP</p>", unsafe_allow_html=True)
        for n in night_ap_list:
            st.markdown(f'''
                <div class="night-ap-card">
                    <div class="name-tag">{n}</div>
                    <div class="ap-tag">Ấp: {dict_ap.get(n)}</div>
                </div>
            ''', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Lỗi: {e}")
