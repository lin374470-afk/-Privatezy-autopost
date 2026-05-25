# 眾贏後台 自動發文系統

電腦關機也能每天自動發文，使用 GitHub Actions 免費雲端執行。

---

## 📁 檔案說明

| 檔案 | 用途 |
|------|------|
| `文章排程表.docx` | 預先填好 20 篇文章內容 |
| `auto_post.py` | 自動發文腳本 |
| `.github/workflows/daily_post.yml` | GitHub Actions 定時排程設定 |

---

## 🚀 一次性設定步驟

### 第一步：註冊 GitHub 帳號
前往 https://github.com 免費註冊

### 第二步：建立新倉庫
1. 點右上角「+」→「New repository」
2. 名稱填：`zy-autopost`（私人 Private）
3. 點「Create repository」

### 第三步：上傳所有檔案
將以下檔案全部上傳到倉庫根目錄：
- `文章排程表.docx`（填好內容後上傳）
- `auto_post.py`
- `.github/workflows/daily_post.yml`

### 第四步：設定帳號密碼（Secrets）
1. 進入倉庫 → 點上方「Settings」
2. 左側選「Secrets and variables」→「Actions」
3. 點「New repository secret」，新增兩個：
   - 名稱：`ZY_USERNAME`　值：您的後台帳號
   - 名稱：`ZY_PASSWORD`　值：您的後台密碼

### 第五步：完成！
設定完畢後，GitHub 每天 UTC 00:00（台灣時間 08:00）
自動啟動腳本，腳本內再隨機延遲 0~60 分鐘後發文。

---

## ✏️ 如何更新文章內容

1. 打開 `文章排程表.docx`，填寫每篇的：
   - 【新聞標題】
   - 【新聞類別】（填：新聞資訊）
   - 【新聞內容】
   - 【簡　　介】（可選）
   - 【SEO簡介】（可選）
   - 【SEO關鍵字】（可選）
   - 【是否熱門】（填：是 或 否）
   - 【狀　　態】保持「待發」，發完後腳本會改為「已發」

2. 上傳更新後的 Word 檔到 GitHub（覆蓋舊檔）

---

## 🔍 查看發文記錄

倉庫 → 上方「Actions」→ 點任一次執行記錄 → 展開「執行自動發文」可看到詳細日誌

---

## ⚠️ 注意事項

- Word 檔中每篇文章的日期格式必須為 `YYYY-MM-DD`（如 2026-05-25）
- 帳密只存在 GitHub Secrets，不會洩漏
- 若後台 IP 限制嚴格導致登入失敗，可在 Issues 回報，我幫您加代理設定
