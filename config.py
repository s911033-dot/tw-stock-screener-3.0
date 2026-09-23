from pathlib import Path

APP_TITLE = "台股全方位量價籌碼戰情室 V2"
DB_PATH = Path(__file__).resolve().parent / "stock_cache.db"
CACHE_TTL_STOCKS = 86400
CACHE_TTL_MARKET = 1800
CACHE_TTL_CHIPS = 7200
CACHE_TTL_BROKER = 43200
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"}
