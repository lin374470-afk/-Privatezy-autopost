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
WORD_PATH = Path(__file__).parent / "文章排程表.docx"
LOGIN_URL = "https://zy-admin-official.jihua-admin.com/mIOMGjpkqP.php/index/login"
ADD_URL   = "https://zy-admin-official.jihua-admin.com/mIOMGjpkqP.php/news/index/add"

# ── 隨機延遲（秒）避免規律被偵測 ──
DELAY_MIN = 0
DELAY_MAX = 3600  # 最多延遲 1 小時


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_word():
    """從 Word 檔解析所有文章，回傳 {日期: {欄位: 值}} 的字典"""
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

    return articles


def post_article(article: dict):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        # 模擬正常瀏覽器 user-agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="zh-TW",
        )
        page = context.new_page()

        # 隱藏 webdriver 特徵
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        log("登入後台...")
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=30000)
        time.sleep(random.uniform(1, 2))

        page.fill('input[placeholder="用户名"]', USERNAME)
        time.sleep(random.uniform(0.3, 0.8))
        page.fill('input[placeholder="密码"]', PASSWORD)
        time.sleep(random.uniform(0.3, 0.8))
        page.click('button:has-text("登 录")')
        page.wait_for_load_state("networkidle", timeout=20000)
        log("登入成功")

        time.sleep(random.uniform(1, 3))

        log("前往新增文章...")
        page.goto(ADD_URL, wait_until="networkidle", timeout=30000)
        time.sleep(random.uniform(2, 3))

        # 標題
        title = article.get("新聞標題", "")
        page.fill('input[name="title"]', title)
        log(f"標題：{title}")

        # 類別
        cat = article.get("新聞類別", "新聞資訊")
        try:
            page.select_option('select[name="category_id"]', label=cat)
        except Exception:
            log("類別選擇失敗，使用預設")

        # 簡介
        summary = article.get("簡介", article.get("簡\u3000\u3000介", ""))
        if summary:
            try:
                page.fill('input[name="summary"], textarea[name="summary"]', summary)
            except Exception:
                pass

        # SEO 簡介
        seo = article.get("SEO簡介", "")
        if seo:
            try:
                page.fill('textarea[name="seo_summary"]', seo)
            except Exception:
                pass

        # SEO 關鍵字
        kw = article.get("SEO關鍵字", "")
        if kw:
            try:
                page.fill('textarea[name="seo_keywords"]', kw)
            except Exception:
                pass

        # 富文本內容（KindEditor iframe）
        content = article.get("新聞內容", "")
        try:
            iframe = page.frame_locator('iframe.ke-edit-iframe').first
            iframe.locator("body").click()
            time.sleep(0.5)
            page.keyboard.press("Control+a")
            page.keyboard.type(content)
            log("內容已填入")
        except Exception as e:
            log(f"iframe 填入失敗，嘗試 JS 注入：{e}")
            try:
                page.evaluate(
                    """(c) => { for(const f of document.querySelectorAll('iframe'))
                        try { f.contentDocument.body.innerHTML = c; } catch(e){} }""",
                    content
                )
            except Exception as e2:
                log(f"JS 注入也失敗：{e2}")

        # 是否熱門
        hot = article.get("是否熱門", "否")
        if hot == "否":
            try:
                page.locator('input[type="radio"][value="0"]').click()
            except Exception:
                pass

        time.sleep(random.uniform(0.5, 1.5))

        # 送出
        page.click('button:has-text("确定")')
        page.wait_for_load_state("networkidle", timeout=20000)
        time.sleep(2)
        log("發文完成！")
        browser.close()


def main():
    today_str = str(date.today())
    log(f"=== 自動發文啟動，今天：{today_str} ===")

    if not USERNAME or not PASSWORD:
        log("❌ 錯誤：未設定帳號密碼（GitHub Secrets: ZY_USERNAME / ZY_PASSWORD）")
        sys.exit(1)

    articles = parse_word()
    log(f"Word 檔共解析到 {len(articles)} 篇文章")

    article = articles.get(today_str)
    if not article:
        log(f"⚠️  找不到今天（{today_str}）的文章，請在 Word 檔填寫對應日期。")
        sys.exit(0)

    status = article.get("狀\u3000\u3000態", article.get("狀態", "待發"))
    if status == "已發":
        log("今天文章已發過，跳過。")
        sys.exit(0)

    title = article.get("新聞標題", "")
    if not title or "請填寫" in title:
        log("❌ 標題未填寫，請更新 Word 檔後重新上傳。")
        sys.exit(1)

    # 隨機延遲
    delay = random.randint(DELAY_MIN, DELAY_MAX)
    h, m = divmod(delay // 60, 60)
    log(f"隨機延遲 {h}h{m}m 後發文...")
    time.sleep(delay)

    log(f"開始發文：{title}")
    post_article(article)
    log("=== 完成 ===")


if __name__ == "__main__":
    main()
