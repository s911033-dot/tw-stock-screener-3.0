import sqlite3
import json
from pathlib import Path
from typing import Iterable
import pandas as pd
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS watchlist (
        code TEXT PRIMARY KEY,
        name TEXT,
        market TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS price_daily (
        ticker TEXT,
        date TEXT,
        open REAL, high REAL, low REAL, close REAL, volume REAL,
        PRIMARY KEY(ticker, date)
    );
    CREATE TABLE IF NOT EXISTS scan_history (
        run_at TEXT DEFAULT CURRENT_TIMESTAMP,
        strategy TEXT,
        results_json TEXT
    );
    """)
    conn.commit(); conn.close()


def load_watchlist() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT code,name,market FROM watchlist ORDER BY code", conn)
    conn.close(); return df


def add_watchlist(rows: Iterable[dict]):
    conn = get_conn()
    conn.executemany(
        "INSERT OR REPLACE INTO watchlist(code,name,market) VALUES(?,?,?)",
        [(r['code'], r.get('name',''), r.get('market','')) for r in rows]
    )
    conn.commit(); conn.close()


def remove_watchlist(code: str):
    conn = get_conn(); conn.execute("DELETE FROM watchlist WHERE code=?", (code,)); conn.commit(); conn.close()


def save_scan(strategy: str, records):
    conn = get_conn()
    conn.execute("INSERT INTO scan_history(strategy,results_json) VALUES(?,?)", (strategy, json.dumps(records, ensure_ascii=False, default=str)))
    conn.commit(); conn.close()


def save_prices(ticker: str, df: pd.DataFrame):
    if df.empty: return
    rows=[]
    for idx, r in df.iterrows():
        date = pd.Timestamp(idx).strftime('%Y-%m-%d')
        rows.append((ticker,date,float(r['Open']),float(r['High']),float(r['Low']),float(r['Close']),float(r['Volume'])))
    conn=get_conn()
    conn.executemany("INSERT OR REPLACE INTO price_daily(ticker,date,open,high,low,close,volume) VALUES(?,?,?,?,?,?,?)", rows)
    conn.commit(); conn.close()
