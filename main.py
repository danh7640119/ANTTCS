import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Cấu hình trang
st.set_page_config(page_title="Lịch trực Công An Xã", layout="wide")

st.title("📋 TRA CỨU LỊCH TRỰC TRỰC TUYẾN")

# 1. Kết nối với Google Sheets
# Bạn dán link Google Sheets của bạn vào đây
url = "https://docs.google.com/spreadsheets/d/1rgdwCmRsZ-awHnyquByljuYaeg915cVzkFTRbd1IasI/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Đọc dữ liệu (skiprows=8 để bỏ qua tiêu đề thừa như file cũ của bạn)
df = conn.read(spreadsheet=url, skiprows=8)

# 3. Hiển thị dữ liệu (Dùng lại logic Card mà tôi đã hướng dẫn bạn trước đó)
# Ví dụ đơn giản:
st.dataframe(df)