# main.py
import os
import pandas as pd
from datetime import datetime
from config import CSV_COLUMNS
from database import load_csv_to_db

def process_files():
    today = datetime.now()
    folder_name = today.strftime('%Y%m%d')
    today_str = today.strftime('%Y-%m-%d')
    
    base_path = os.path.join(os.getcwd(), folder_name)
    
    if not os.path.exists(base_path):
        print(f"❌ Không tìm thấy thư mục: {folder_name}")
        return

    print(f"📂 Đang quét thư mục chứa file Excel: {base_path}")
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            # Thay đổi từ .csv sang .xlsx
            if file.endswith('.xlsx') or file.endswith('.xls'):
                file_path = os.path.join(root, file)
                ma_cp = os.path.splitext(file)[0].upper()[:3]
                print(f"\n🚀 Đang xử lý mã: {ma_cp} (File: {file})")
                
                # File tạm vẫn để đuôi .csv để MySQL LOAD DATA dễ dàng
                temp_csv_path = os.path.join(root, f"temp_{ma_cp}.csv")
                
                try:
                    # 1. Đọc file Excel bằng Pandas
                    # Thêm engine='openpyxl' để đọc file .xlsx chuẩn nhất
                    df = pd.read_excel(file_path, engine='openpyxl')
                    
                    # Làm sạch tên cột
                    df.columns = df.columns.str.strip()
                    
                    # Kiểm tra cột (CSV_COLUMNS trong config nên đổi tên cho phù hợp, 
                    # nhưng logic vẫn là check danh sách tên cột)
                    if not all(col in df.columns for col in CSV_COLUMNS):
                        print(f"⚠️ File {file} thiếu cột cần thiết. Cột hiện tại: {df.columns.tolist()}")
                        continue

                    # 2. Chuẩn hóa dữ liệu bằng Pandas (Vectorization - cực nhanh)
                    df['ma_cp'] = ma_cp
                    
                    # Xử lý thời gian: Excel thường đã nhận diện là kiểu time/datetime
                    # Nếu là kiểu time của Excel, ta ép về string rồi ghép ngày
                    df['thoi_gian'] = pd.to_datetime(today_str + ' ' + df['Thời gian'].astype(str))
                    
                    # Ép kiểu số, xóa dấu phẩy nếu có (thường Excel đã tự định dạng số nên bước này rất an toàn)
                    df['khoi_luong'] = pd.to_numeric(df['KL'].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
                    df['gia'] = pd.to_numeric(df['Giá'].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(float)
                    
                    df['thay_doi'] = df['+/-']
                    df['thay_doi_phan_tram'] = df['+/-%']
                    df['hanh_dong'] = df['M/B']

                    # 3. Lọc lại đúng thứ tự cột để khớp với câu lệnh LOAD DATA trong database.py
                    db_columns = ['ma_cp', 'thoi_gian', 'khoi_luong', 'gia', 'thay_doi', 'thay_doi_phan_tram', 'hanh_dong']
                    df_final = df[db_columns]
                    
                    # 4. Lưu ra file CSV tạm (không lấy tiêu đề, dùng dấu phẩy ngăn cách)
                    # encoding='utf-8' giúp MySQL đọc được tiếng Việt nếu có
                    df_final.to_csv(temp_csv_path, index=False, header=False, encoding='utf-8')

                    # 5. Gọi hàm LOAD DATA từ module database
                    inserted_rows = load_csv_to_db(temp_csv_path)
                    
                    if inserted_rows > 0:
                        print(f"✅ Đã import {inserted_rows} dòng của {ma_cp} vào MySQL.")
                    else:
                        print(f"⚠️ Không có dữ liệu được thêm cho {ma_cp}.")

                except Exception as e:
                    print(f"❌ Lỗi xử lý file Excel {file}: {e}")
                
                finally:
                    # 6. Dọn dẹp file tạm
                    if os.path.exists(temp_csv_path):
                        os.remove(temp_csv_path)

if __name__ == "__main__":
    process_files()