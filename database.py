# database.py
import mysql.connector
from config import DB_CONFIG, TABLE_NAME

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"❌ Lỗi kết nối Database: {err}")
        return None

def load_csv_to_db(csv_file_path):
    """Sử dụng LOAD DATA LOCAL INFILE để đẩy tốc độ lên tối đa"""
    connection = get_connection()
    if not connection:
        return 0

    try:
        cursor = connection.cursor()
        
        # MySQL cần đường dẫn file dùng dấu '/' (forward slash), kể cả trên Windows
        csv_path_for_mysql = csv_file_path.replace('\\', '/')

        query = f"""
            LOAD DATA LOCAL INFILE '{csv_path_for_mysql}'
            INTO TABLE {TABLE_NAME}
            FIELDS TERMINATED BY ',' 
            ENCLOSED BY '"'
            LINES TERMINATED BY '\\n'
            (ma_cp, thoi_gian, khoi_luong, gia, thay_doi, thay_doi_phan_tram, hanh_dong)
        """
        
        cursor.execute(query)
        connection.commit()
        
        row_count = cursor.rowcount
        cursor.close()
        return row_count

    except mysql.connector.Error as err:
        print(f"❌ Lỗi MySQL khi thực thi LOAD DATA: {err}")
        return 0
    finally:
        if connection and connection.is_connected():
            connection.close()