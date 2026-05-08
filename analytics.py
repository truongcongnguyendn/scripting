import warnings
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime
from config import DB_CONFIG

# Suppress annoying Pandas SQLAlchemy warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------
# ANSI COLOR CODES FOR TERMINAL STYLING (HACKER THEME)
# ---------------------------------------------------------
C_RESET = '\033[0m'
C_RED = '\033[91m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_BLUE = '\033[94m'
C_MAGENTA = '\033[95m'
C_CYAN = '\033[96m'
C_BOLD = '\033[1m'

# ---------------------------------------------------------
# DATABASE ENGINE INITIALIZATION
# ---------------------------------------------------------
# Construct SQLAlchemy URI from your DB_CONFIG
DB_URI = f"mysql+mysqlconnector://{DB_CONFIG.get('user')}:{DB_CONFIG.get('password')}@{DB_CONFIG.get('host')}/{DB_CONFIG.get('database')}"

# Create a single global engine for efficient connection pooling
engine = create_engine(DB_URI)


def lay_danh_sach_ma_da_giao_dich(ngay_chon):
    """
    Retrieve a distinct list of stock tickers that have recorded transactions 
    on the specified date.
    """
    danh_sach = []
    try:
        query = text("SELECT DISTINCT ma_cp FROM all_trans WHERE DATE(thoi_gian) = :ngay_chon")
        with engine.connect() as conn:
            result = conn.execute(query, {"ngay_chon": ngay_chon})
            danh_sach = [row[0] for row in result]
    except Exception as err:
        print(f"{C_RED}❌ Error fetching ticker list: {err}{C_RESET}")
    return danh_sach


def phan_tich_all_trans(ma_cp, ngay_giao_dich):
    """
    Fetch intraday transaction data for a specific ticker and perform 
    advanced volume profile and market maker behavioral analysis.
    """
    print(f"{C_CYAN}⏳ Extracting order flow for {C_YELLOW}{C_BOLD}{ma_cp}{C_RESET}{C_CYAN} on {ngay_giao_dich}...{C_RESET}")
    
    try:
        query = text("""
            SELECT thoi_gian, gia, khoi_luong, hanh_dong 
            FROM all_trans 
            WHERE ma_cp = :ma_cp AND DATE(thoi_gian) = :ngay_giao_dich
            ORDER BY thoi_gian ASC
        """)
        
        df = pd.read_sql(query, engine, params={"ma_cp": ma_cp, "ngay_giao_dich": ngay_giao_dich})
        
        if df.empty:
            print(f"{C_YELLOW}⚠️ No transactions found for {ma_cp} on {ngay_giao_dich}.{C_RESET}")
            return
            
    except Exception as err:
        print(f"{C_RED}❌ Database query error for {ma_cp}: {err}{C_RESET}")
        return

    # ---------------------------------------------------------
    # PANDAS DATA ANALYSIS & REPORT GENERATION
    # ---------------------------------------------------------
    print(f"\n{C_MAGENTA}{'='*60}{C_RESET}")
    print(f"{C_MAGENTA}{C_BOLD}📊 TRADING BEHAVIOR ANALYSIS: {C_YELLOW}{ma_cp}{C_RESET}")
    print(f"{C_MAGENTA}{'='*60}{C_RESET}\n")

    # Clean and cast data types
    df['gia'] = pd.to_numeric(df['gia'])
    df['khoi_luong'] = pd.to_numeric(df['khoi_luong'])
    df['thoi_gian'] = pd.to_datetime(df['thoi_gian'])
    
    # --- 1. OVERALL TRANSACTION METRICS ---
    tong_kl = df['khoi_luong'].sum()
    kl_mua = df[df['hanh_dong'] == 'M']['khoi_luong'].sum()
    kl_ban = df[df['hanh_dong'] == 'B']['khoi_luong'].sum()
    so_lenh = len(df)
    
    gia_trung_binh = (df['gia'] * df['khoi_luong']).sum() / tong_kl if tong_kl > 0 else 0
    gia_cao_nhat = df['gia'].max()
    gia_thap_nhat = df['gia'].min()

    print(f"{C_CYAN}{C_BOLD}[1] TỔNG QUAN GIAO DỊCH (OVERVIEW):{C_RESET}")
    print(f"  - Tổng KL khớp: {C_BOLD}{tong_kl:,.0f} CP{C_RESET} ({so_lenh:,.0f} lệnh)")
    if tong_kl:
        print(f"  - Lượng Bán (B): {C_RED}{kl_ban:,.0f} CP ({kl_ban/tong_kl*100:.1f}%){C_RESET}")
        print(f"  - Lượng Mua (M): {C_GREEN}{kl_mua:,.0f} CP ({kl_mua/tong_kl*100:.1f}%){C_RESET}")
    print(f"  - Giá trung bình (VWAP): {C_YELLOW}~{gia_trung_binh:,.3f} VNĐ{C_RESET}")
    print(f"  - Biên độ giá: {gia_thap_nhat:,.2f} VNĐ - {gia_cao_nhat:,.2f} VNĐ\n")

    # --- 2. VOLUME PROFILE (SUPPORT / RESISTANCE ZONES) ---
    vung_gia_chitiet = df.groupby(['gia', 'hanh_dong'])['khoi_luong'].sum().unstack(fill_value=0)
    
    if 'M' not in vung_gia_chitiet.columns: vung_gia_chitiet['M'] = 0
    if 'B' not in vung_gia_chitiet.columns: vung_gia_chitiet['B'] = 0
        
    vung_gia_chitiet['Tong'] = vung_gia_chitiet['M'] + vung_gia_chitiet['B']
    top_vung_gia = vung_gia_chitiet.sort_values(by='Tong', ascending=False).head(3)
    
    print(f"{C_CYAN}{C_BOLD}[2] VOLUME PROFILE & VÙNG THANH KHOẢN:{C_RESET}")
    for gia, row in top_vung_gia.iterrows():
        tong = row['Tong']
        mua, ban = row['M'], row['B']
        p_mua = (mua / tong) * 100 if tong > 0 else 0
        p_ban = (ban / tong) * 100 if tong > 0 else 0
        
        if p_ban >= 60: nhan_xet_vung = f"{C_RED}🔴 Bị xả mạnh{C_RESET}"
        elif p_mua >= 60: nhan_xet_vung = f"{C_GREEN}🟢 Cầu đỡ tốt{C_RESET}"
        else: nhan_xet_vung = f"⚪ Giằng co"

        print(f"  {C_BOLD}📍 Giá {gia:,.2f}{C_RESET}: {tong:,.0f} CP")
        print(f"     ↳ Mua: {C_GREEN}{mua:,.0f} ({p_mua:.1f}%){C_RESET} | Bán: {C_RED}{ban:,.0f} ({p_ban:.1f}%){C_RESET} -> {nhan_xet_vung}")
    print()

    # --- 3. WHALE TRACKING (TOP TRANSACTIONS) ---
    top_5_gd = df.nlargest(5, 'khoi_luong')
    print(f"{C_CYAN}{C_BOLD}[3] WHALE TRACKING (TOP 5 LỆNH LỚN NHẤT):{C_RESET}")
    for _, row in top_5_gd.iterrows():
        tg_str = row['thoi_gian'].strftime('%H:%M:%S') 
        hd_str = f"{C_GREEN}Mua{C_RESET}" if row['hanh_dong'] == 'M' else f"{C_RED}Bán{C_RESET}"
        print(f"  🦈 {tg_str}: {C_BOLD}{row['khoi_luong']:,.0f} CP{C_RESET} - Giá {row['gia']:,.2f} ({hd_str})")
    print()

    # --- 4. MARKET MAKER PROFILING (PHÂN TÍCH HÀNH VI TẠO LẬP) ---
    print(f"{C_CYAN}{C_BOLD}[4] PHÂN TÍCH HÀNH VI DÒNG TIỀN (ORDER SIZING & CVD):{C_RESET}")
    
    # 4.1 Categorize Orders by Size (Nhỏ lẻ, Tầm trung, Cá mập)
    bins = [0, 5000, 50000, float('inf')]
    labels = ['Nhỏ lẻ (<5k)', 'Tầm trung (5k-50k)', 'Cá mập (>50k)']
    
    # pd.cut automatically assigns categories based on the volume
    df['phan_lop'] = pd.cut(df['khoi_luong'], bins=bins, labels=labels, include_lowest=True)
    
    # Group by the new category
    phan_lop_df = df.groupby(['phan_lop', 'hanh_dong'])['khoi_luong'].sum().unstack(fill_value=0)
    if 'M' not in phan_lop_df: phan_lop_df['M'] = 0
    if 'B' not in phan_lop_df: phan_lop_df['B'] = 0
    
    # Calculate Net Volume (CVD per category)
    phan_lop_df['Net'] = phan_lop_df['M'] - phan_lop_df['B']
    
    for idx in labels:
        if idx in phan_lop_df.index:
            mua_lop = phan_lop_df.loc[idx, 'M']
            ban_lop = phan_lop_df.loc[idx, 'B']
            net_lop = phan_lop_df.loc[idx, 'Net']
            
            # Formatting based on who is winning
            if net_lop > 0:
                trend = f"{C_GREEN}MUA RÒNG (+{net_lop:,.0f} CP){C_RESET}"
            elif net_lop < 0:
                trend = f"{C_RED}BÁN RÒNG ({net_lop:,.0f} CP){C_RESET}"
            else:
                trend = f"CÂN BẰNG"
                
            print(f"  - {C_BOLD}{idx}{C_RESET}: {trend}")
            print(f"    ↳ Tổng Mua: {mua_lop:,.0f} | Tổng Bán: {ban_lop:,.0f}")
            
    # 4.2 Cumulative Volume Delta (CVD) Analysis
    # Tính khối lượng ròng toàn phiên: Mua là dương (+), Bán là âm (-)
    df['signed_vol'] = np.where(df['hanh_dong'] == 'M', df['khoi_luong'], -df['khoi_luong'])
    final_cvd = df['signed_vol'].sum()
    
    print(f"\n  {C_BOLD}CVD (Cumulative Volume Delta) toàn phiên:{C_RESET}", end=" ")
    if final_cvd > 0:
        print(f"{C_GREEN}+{final_cvd:,.0f} CP (Phe Mua nắm quyền kiểm soát){C_RESET}")
    elif final_cvd < 0:
        print(f"{C_RED}{final_cvd:,.0f} CP (Phe Bán dồn ép thị trường){C_RESET}")
    else:
        print(f"0 CP (Giằng co tuyệt đối)")

    # 4.3 Detect Distribution/Accumulation Traps (Phát hiện bẫy giá)
    try:
        net_camap = phan_lop_df.loc['Cá mập (>50k)', 'Net']
        net_nhole = phan_lop_df.loc['Nhỏ lẻ (<5k)', 'Net']
        
        if net_camap < 0 and net_nhole > 0:
            print(f"\n  {C_RED}{C_BOLD}⚠️ CẢNH BÁO BẪY PHÂN PHỐI:{C_RESET}{C_RED} Cá mập đang xả hàng cho Nhỏ lẻ ôm!{C_RESET}")
        elif net_camap > 0 and net_nhole < 0:
            print(f"\n  {C_GREEN}{C_BOLD}🚀 DẤU HIỆU GOM HÀNG:{C_RESET}{C_GREEN} Tay to đang mua gom những lệnh cắt lỗ của Nhỏ lẻ!{C_RESET}")
    except KeyError:
        # Prevent errors if there are no 'Cá mập' trades in a very illiquid stock
        pass


# =========================================================
# MAIN EXECUTION THREAD
# =========================================================
if __name__ == '__main__':
    # You can customize the date here. Defaults to current date.
    curr_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"{C_MAGENTA}{'='*70}{C_RESET}")
    print(f"{C_MAGENTA}{C_BOLD}🚀 QUANTITATIVE MARKET ENGINE INITIATED - DATE: {curr_date}{C_RESET}")
    print(f"{C_MAGENTA}{'='*70}{C_RESET}\n")
    
    all_tickers = lay_danh_sach_ma_da_giao_dich(ngay_chon=curr_date)
    
    if not all_tickers:
        print(f"{C_YELLOW}⚠️ Hệ thống chưa ghi nhận mã nào có dữ liệu trong ngày {curr_date}.{C_RESET}")
    else:
        print(f"{C_GREEN}✅ Load thành công {len(all_tickers)} mã. Đang tiến hành xử lý...{C_RESET}\n")
        
        for ticker in all_tickers:
            phan_tich_all_trans(ma_cp=ticker, ngay_giao_dich=curr_date)
            
    print(f"\n{C_MAGENTA}🏁 TASK COMPLETED SUCCESSFULLY!{C_RESET}")