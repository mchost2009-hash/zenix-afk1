from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import time, os, json, base64, requests
from datetime import datetime

EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
GH_TOKEN = os.environ.get("GH_TOKEN")
REPO = "LVT382009/zenix-afk"

def push_stats(stats):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/stats.json"
        headers = {
            "Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        content = base64.b64encode(json.dumps(stats, ensure_ascii=False, indent=2).encode()).decode()

        # Lấy SHA file cũ nếu có
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None

        data = {"message": "Update stats", "content": content}
        if sha:
            data["sha"] = sha

        requests.put(url, headers=headers, json=data)
        print("📤 Đã push stats lên GitHub!")
    except Exception as e:
        print(f"⚠️ Push thất bại: {e}")

def load_stats():
    try:
        with open("stats.json", "r") as f:
            return json.load(f)
    except:
        return {
            "total_coins": 0,
            "start_coin": 0,
            "coins_per_hour": 0,
            "coins_today": 0,
            "today_date": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": "",
            "logs": []
        }

def save_stats(stats):
    with open("stats.json", "w") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def add_log(stats, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"{timestamp} - {message}"
    stats["logs"].insert(0, log_entry)
    stats["logs"] = stats["logs"][:50]
    print(log_entry)

def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    chromedriver_autoinstaller.install()
    return webdriver.Chrome(options=options)

def login(driver, email, password):
    print("🔐 Đang login...")
    driver.get("https://dash.zenix.sg/login")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(3)
    print("✅ Đã login thành công!")

def get_coins(driver):
    try:
        coin_span = driver.find_element(
            By.CSS_SELECTOR,
            "div.bg-blue-950\\/30 span.font-semibold.text-blue-400"
        )
        return int(coin_span.text.strip())
    except:
        return None

def reset_afk(driver, stats):
    add_log(stats, "🔄 Reset AFK - Coin không tăng!")
    driver.get("https://dash.zenix.sg/dashboard")
    time.sleep(2)
    driver.get("https://dash.zenix.sg/dashboard/afk")
    time.sleep(2)
    add_log(stats, "✅ Reset xong!")

def stay_afk(driver):
    stats = load_stats()
    print("🚀 Đang vào trang AFK...")
    driver.get("https://dash.zenix.sg/dashboard/afk")
    time.sleep(2)

    start_time = datetime.now()
    count = 0
    last_coin = get_coins(driver)
    stats["start_coin"] = last_coin

    today = datetime.now().strftime("%Y-%m-%d")
    if stats["today_date"] != today:
        stats["coins_today"] = 0
        stats["today_date"] = today

    add_log(stats, f"🚀 Bắt đầu AFK | 💰 Coin: {last_coin}")
    save_stats(stats)
    push_stats(stats)  # Push ngay lần đầu

    while True:
        time.sleep(60)
        count += 1
        current_coin = get_coins(driver)
        now = datetime.now()

        # Tính coin/giờ
        elapsed_hours = (now - start_time).seconds / 3600
        if elapsed_hours > 0 and current_coin:
            coins_earned = current_coin - stats["start_coin"]
            stats["coins_per_hour"] = round(coins_earned / elapsed_hours, 1)

        # Coin hôm nay
        if current_coin and last_coin:
            gained = current_coin - last_coin
            if gained > 0:
                stats["coins_today"] += gained

        stats["total_coins"] = current_coin or 0
        stats["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")

        if current_coin is None or current_coin <= last_coin:
            reset_afk(driver, stats)
            last_coin = get_coins(driver)
            add_log(stats, f"💰 Coin sau reset: {last_coin}")
        else:
            add_log(stats, f"✅ +{current_coin - last_coin} coin | Tổng: {current_coin}")
            last_coin = current_coin

        save_stats(stats)
        push_stats(stats)  # Push mỗi phút

if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("❌ Lỗi: Không tìm thấy EMAIL hoặc PASSWORD!")
        exit(1)

    driver = create_driver()
    try:
        login(driver, EMAIL, PASSWORD)
        stay_afk(driver)
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        driver.quit()
