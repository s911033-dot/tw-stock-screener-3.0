# 台股全方位量價籌碼戰情室 V2.1

Streamlit 台股研究型選股工具，加入：

- 技術 × 量價 × 法人 × 融資 × 分點
- 多因子權重調整介面
- 多因子每日回測引擎
- 策略績效統計：累積報酬、年化報酬、波動、Sharpe、最大回撤、勝率、月報酬
- 自動每日資料更新 GitHub Actions
- CSV / Excel 匯出
- SQLite 自選股與掃描紀錄

## 回測設計

回測採「T 日收盤產生訊號 → T+1 日開盤進場 → T+1 日收盤計算報酬」，避免直接把 T+1 的價格拿來產生 T 日訊號。每日選出分數最高且達門檻的 Top N 股票，等權配置；交易成本為簡化估計值。

這不是券商級撮合回測器，未完整模擬滑價、流動性、漲跌停、零股成交、稅費差異等。

## 自動每日更新

`.github/workflows/daily_update.yml` 會在台灣時間平日下午約 16:30 執行，也可在 GitHub Actions 手動觸發。它會產生 `data/daily_snapshot.csv` 並自動 commit。

> 若 GitHub 儲存庫設為公開，請注意資料檔大小；若未來改成大量歷史資料，建議改用資料庫或雲端物件儲存，不要把大型 SQLite 檔持續 commit。

## 本機執行

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## GitHub

```bash
git init
git add .
git commit -m "Add Taiwan stock screener V2.1"
git branch -M main
git remote add origin YOUR_REPO_URL
git push -u origin main
```

## FinMind Token（可選）

建立 `.streamlit/secrets.toml`：

```toml
FINMIND_TOKEN = "YOUR_TOKEN"
```

`.gitignore` 已排除 secrets。

## 注意

資料來源可能延遲、缺漏或更改 API 格式；回測結果是歷史資料模擬，不代表未來績效，也不構成投資建議。
