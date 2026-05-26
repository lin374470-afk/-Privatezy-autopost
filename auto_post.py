"""
自動發文腳本 — 讀取 Word 檔 + Playwright 發文到眾贏後台
部署在 GitHub Actions，每天自動執行
"""
import os, re, sys, random, time
from datetime import date, datetime
from pathlib import Path
from docx import Document
from playwright.sync_api import sync_playwright

# ── 設定（GitHub Actions 用 Secrets，本地測試可直接填） ──
USERNAME = os.environ.get("ZY_USERNAME", "")
PASSWORD = os.environ.get("ZY_PASSWORD", "")
WORD_PATH = Path(__file__).parent / "文章排程表_6月.docx"
LOGIN_URL = "https://zy-admin-official.jihua-admin.com/mIOMGjpkqP.php/index/login"
ADD_URL   = "https://zy-admin-official.jihua-admin.com/mIOMGjpkqP.php/news/index/add"

# ── 隨機延遲（秒）避免規律被偵測 ──
DELAY_MIN = 0
DELAY_MAX = 3600  # 最多延遲 1 小時


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_word():
    """從 Word 檔解析所有文章，回傳 {日期: {欄位: 值}} 的字典"""
    # 檢查文件是否存在
    if not WORD_PATH.exists():
        log(f"❌ 錯誤：找不到 Word 檔案：{WORD_PATH}")
        log("   請將 '文章排程表_6月.docx' 上傳到仓库根目录")
        sys.exit(1)
    
    log(f"✓ Word 檔案找到：{WORD_PATH}")
    doc = Document(WORD_PATH)
    articles = {}
    current = {}
    current_date = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # 標題列：第 N 篇　日期：YYYY-MM-DD
        m = re.search(r'日期[：:]\s*(\d{4}-\d{2}-\d{2})', text)
        if m:
            if current_date and current:
                articles[current_date] = current
                log(f"  → 解析到日期 {current_date}，欄位數：{len(current)}")
            current_date = m.group(1)
            current = {}
            continue

        # 欄位列：【欄位名】 值
        m2 = re.match(r'【(.+?)】\s*(.*)', text)
        if m2 and current_date is not None:
            key = m2.group(1).strip().replace('\u3000', '').replace(' ', '')
            val = m2.group(2).strip()
            current[key] = val

    if current_date and current:
        articles[current_date] = current
        log(f"  → 解析到日期 {current_date}，欄位數：{len(current)}")

    return articles


def post_article(article: dict):
    log("🚀 開始發文流程...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        log("✓ 瀏覽器已啟動")
        
        # 模擬正常瀏覽器 user-agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="zh-TW",
        )
        page = context.new_page()
        log("✓ 頁面上下文已建立")

        # 隱藏 webdriver 特徵
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        try:
            log("📝 登入後台...")
            page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
            time.sleep(random.uniform(1, 2))
            log(f"  ✓ 頁面加載完成，URL: {page.url}")

            page.fill('input[placeholder="用户名"]', USERNAME)
            log(f"  ✓ 已填入用户名")
            time.sleep(random.uniform(0.3, 0.8))
            
            page.fill('input[placeholder="密码"]', PASSWORD)
            log(f"  ✓ 已填入密码")
            time.sleep(random.uniform(0.3, 0.8))
            
            page.click('button:has-text("登 录")')
            log(f"  ✓ 已點擊登錄按鈕")
            page.wait_for_load_state("networkidle", timeout=20000)
            log("✅ 登入成功")
            log(f"  → 當前 URL: {page.url}")

            time.sleep(random.uniform(1, 3))

            log("📝 前往新增文章頁面...")
            page.goto(ADD_URL, wait_until="networkidle", timeout=30000)
            log(f"✓ 頁面加載完成，URL: {page.url}")
            time.sleep(random.uniform(2, 3))

            # 標題
            title = article.get("新聞標題", "")
            log(f"📌 標題：{title}")
            page.fill('input[name="title"]', title)
            log(f"  ✓ 已填入標題")

            # 類別
            cat = article.get("新聞類別", "新聞資訊")
            log(f"📌 類別：{cat}")
            try:
                page.select_option('select[name="category_id"]', label=cat)
                log(f"  ✓ 已選擇類別")
            except Exception as e:
                log(f"  ⚠️  類別選擇失敗：{e}，使用預設")

            # 簡介
            summary = article.get("簡介", article.get("簡\u3000\u3000介", ""))
            if summary:
                log(f"📌 簡介：{summary[:50]}...")
                try:
                    page.fill('input[name="summary"], textarea[name="summary"]', summary)
                    log(f"  ✓ 已填入簡介")
                except Exception as e:
                    log(f"  ⚠️  簡介填入失敗：{e}")

            # SEO 簡介
            seo = article.get("SEO簡介", "")
            if seo:
                log(f"📌 SEO簡介：{seo[:50]}...")
                try:
                    page.fill('textarea[name="seo_summary"]', seo)
                    log(f"  ✓ 已填入 SEO 簡介")
                except Exception as e:
                    log(f"  ⚠️  SEO 簡介填入失敗：{e}")

            # SEO 關鍵字
            kw = article.get("SEO關鍵字", "")
            if kw:
                log(f"📌 SEO關鍵字：{kw}")
                try:
                    page.fill('textarea[name="seo_keywords"]', kw)
                    log(f"  ✓ 已填入 SEO 關鍵字")
                except Exception as e:
                    log(f"  ⚠️  SEO 關鍵字填入失敗：{e}")

            # 富文本內容（KindEditor iframe）
            content = article.get("新聞內容", "")
            log(f"📌 內容長度：{len(content)} 字")
            try:
                iframe = page.frame_locator('iframe.ke-edit-iframe').first
                iframe.locator("body").click()
                time.sleep(0.5)
                page.keyboard.press("Control+a")
                page.keyboard.type(content)
                log("✓ iframe 內容已填入")
            except Exception as e:
                log(f"⚠️  iframe 填入失敗，嘗試 JS 注入：{e}")
                try:
                    page.evaluate(
                        """(c) => { for(const f of document.querySelectorAll('iframe'))
                            try { f.contentDocument.body.innerHTML = c; } catch(e){} }""",
                        content
                    )
                    log("✓ JS 注入成功")
                except Exception as e2:
                    log(f"❌ JS 注入也失敗：{e2}")

            # 是否熱門
            hot = article.get("是否熱門", "否")
            log(f"📌 是否熱門：{hot}")
            if hot == "否":
                try:
                    page.locator('input[type="radio"][value="0"]').click()
                    log(f"  ✓ 已設定為非熱門")
                except Exception as e:
                    log(f"  ⚠️  熱門設定失敗：{e}")

            time.sleep(random.uniform(0.5, 1.5))

            # 送出
            log("📤 點擊提交按鈕...")
            page.click('button:has-text("确定")')
            log("  ✓ 已點擊提交")
            page.wait_for_load_state("networkidle", timeout=20000)
            log(f"✓ 頁面加載完成，URL: {page.url}")
            time.sleep(2)
            log("✅ 發文完成！")
            browser.close()

        except Exception as e:
            log(f"❌ 發文過程出錯：{e}")
            log(f"  → 當前 URL: {page.url}")
            browser.close()
            raise


def main():
    today_str = str(date.today())
    log(f"{'='*60}")
    log(f"=== 自動發文啟動，今天：{today_str} ===")
    log(f"{'='*60}")

    if not USERNAME or not PASSWORD:
        log("❌ 錯誤：未設定帳號密碼（GitHub Secrets: ZY_USERNAME / ZY_PASSWORD）")
        sys.exit(1)

    log("📖 解析 Word 檔案...")
    articles = parse_word()
    log(f"✓ Word 檔共解析到 {len(articles)} 篇文章")
    log(f"  → 日期列表：{', '.join(sorted(articles.keys()))}")

    article = articles.get(today_str)
    if not article:
        log(f"⚠️  找不到今天（{today_str}）的文章")
        log(f"  → 可用日期：{', '.join(sorted(articles.keys()))}")
        log("   請在 Word 檔填寫對應日期的文章。")
        sys.exit(0)

    log(f"✓ 找到今天的文章，欄位數：{len(article)}")
    log(f"  → 欄位：{', '.join(article.keys())}")

    status = article.get("狀\u3000\u3000態", article.get("狀態", "待發"))
    log(f"📌 文章狀態：{status}")
    if status == "已發":
        log("⏭️  今天文章已發過，跳過。")
        sys.exit(0)

    title = article.get("新聞標題", "")
    if not title or "請填寫" in title:
        log("❌ 錯誤：標題未填寫或為預設值")
        log("   請更新 Word 檔後重新上傳。")
        sys.exit(1)

    log(f"✓ 文章標題有效：{title}")

    # 隨機延遲
    delay = random.randint(DELAY_MIN, DELAY_MAX)
    h, m = divmod(delay // 60, 60)
    if delay > 0:
        log(f"⏳ 隨機延遲 {h}h{m}m 後發文...")
        time.sleep(delay)
    else:
        log(f"✓ 無延遲，立即開始發文")

    log(f"🚀 開始發文：{title}")
    post_article(article)
    log(f"{'='*60}")
    log("=== 完成 ===")
    log(f"{'='*60}")


if __name__ == "__main__":
    main()
