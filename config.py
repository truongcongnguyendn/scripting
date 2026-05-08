# config.py
from mysql.connector.constants import ClientFlag

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123654789',
    'database': 'stocks_info',
    'allow_local_infile': True,
    'client_flags': [ClientFlag.LOCAL_FILES]
}

# Tên bảng trong database
TABLE_NAME = 'all_trans'

# Cấu hình các cột (tên cột trong CSV)
CSV_COLUMNS = ['Thời gian', 'KL', 'Giá', '+/-', '+/-%', 'M/B']

# Create tables
SQL = """
    CREATE TABLE all_trans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        ma_cp VARCHAR(10) NOT NULL,
        thoi_gian DATETIME NOT NULL,
        khoi_luong INT,
        gia DECIMAL(10, 2),
        thay_doi DECIMAL(10, 2),
        thay_doi_phan_tram DECIMAL(5, 2),
        hanh_dong VARCHAR(5),
        INDEX idx_macp_thoigian (ma_cp, thoi_gian)
    );
"""

VNSTOCK_API_KEY = "vnstock_ab68b43f21efe93a0588cd035a59e062"