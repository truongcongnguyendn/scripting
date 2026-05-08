from vnstock import register_user, Listing, Trading
import pandas as pd
import time
from datetime import datetime
from vnstock import Quote
import mysql.connector # Nhớ cài đặt: pip install mysql-connector-python
from config import VNSTOCK_API_KEY, DB_CONFIG # Giả sử DB_CONFIG là dict chứa host, user, pass...

register_user(VNSTOCK_API_KEY)

def lay_gia_hose_vnstock3():
    print("⏳ Đang tải danh sách mã HOSE bằng Vnstock3...")
    today = datetime.now().date()
    
    # 1. Khởi tạo module Listing và lấy danh sách mã
    listing = Listing(source='KBS')
    df_danh_sach = listing.all_symbols()
    all_stocks = df_danh_sach.to_dict(orient='records')

    # Mở kết nối Database một lần duy nhất trước khi chạy vòng lặp
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        for stock in all_stocks:
            ma_cp = stock['symbol']
            print(f"\n🚀 Đang lấy giá cho mã: {ma_cp}")
            
            try:
                quote = Quote(symbol=ma_cp, source='VCI')
                df = quote.history(start=str(today), end=str(today), interval='d')

                if df is None or df.empty:
                    print("⚠️ Không lấy được dữ liệu. Có thể đã đụng trần API (Rate Limit).")
                    print("⏳ Nghỉ ngơi 60 giây để reset quota...")
                    time.sleep(60)
                    # Thử lấy lại mã này một lần nữa sau khi đã nghỉ
                    df = quote.history(start=str(today), end=str(today), interval='d')
                    if df is None or df.empty:
                        print(f"⏭️ Vẫn không lấy được mã {ma_cp}, bỏ qua để sang mã tiếp theo.")
                        continue
                
                df_today = pd.DataFrame() # Reset tránh dùng dữ liệu cũ
                if not df.empty:
                    df['time_date'] = pd.to_datetime(df['time']).dt.date
                    df_today = df[df['time_date'] == today]
                
                if not df_today.empty:
                    record = df_today.head(1).to_dict(orient='records')[0]
                    record['time'] = record['time'].strftime('%Y-%m-%d')
                    
                    print(f"Dữ liệu chuẩn ngày hôm nay ({today}): {record}")

                    ######## CODE ĐOẠN LUƯ Ý ĐỂ LƯU VÀO DATABASE Ở ĐÂY ########
                    ######## CODE ĐOẠN LƯU VÀO DATABASE ########
                    # Lưu ý: Đã thêm đủ 7 dấu %s tương ứng với 7 cột
                    sql = """
                        INSERT INTO stock_price (ticker, time, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            open=VALUES(open), 
                            high=VALUES(high), 
                            low=VALUES(low), 
                            close=VALUES(close), 
                            volume=VALUES(volume)
                    """
                    
                    # Tuple này có 7 phần tử, khớp hoàn toàn với 7 dấu %s ở trên
                    val = (
                        ma_cp, 
                        record['time'], 
                        record['open'], 
                        record['high'], 
                        record['low'], 
                        record['close'], 
                        record['volume']
                    )
                    
                    cursor.execute(sql, val)
                    conn.commit()
                    print(f"✅ Đã cập nhật database cho mã: {ma_cp}")
                else:
                    print(f"Chưa có dữ liệu khớp chính xác ngày {today}")
                
            except Exception as e:
                print(f"❌ Lỗi khi lấy dữ liệu mã {ma_cp}: {e}")

            # Nghỉ 0.5s để tránh bị block API (60 req/min cho gói Community)
            time.sleep(1.5)

    except mysql.connector.Error as err:
        print(f"❌ Lỗi kết nối Database: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("\n🔌 Đã đóng kết nối Database.")

if __name__ == '__main__':
    lay_gia_hose_vnstock3()