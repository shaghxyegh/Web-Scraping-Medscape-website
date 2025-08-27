import csv
import json
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


def accept_cookies_if_present(driver, wait):
    """Accept Medscape cookie popup if it appears"""
    try:
        accept_button = wait.until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        accept_button.click()
        print("✅ Clicked cookie consent button.")
        time.sleep(1)
    except TimeoutException:
        print("⚠️ No cookie popup found.")


def remove_cookie_overlay(driver):
    """Remove dark overlay layer after cookie popup"""
    try:
        overlay = driver.find_element(By.CSS_SELECTOR, ".onetrust-pc-dark-filter")
        driver.execute_script("arguments[0].style.display = 'none';", overlay)
        print("✅ Removed cookie overlay.")
    except Exception:
        pass


def simulate_human_behavior(driver):
    """Scroll down a bit to simulate human and trigger lazy loading"""
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 3))
    except Exception as e:
        print(f"⚠️ Error in simulate_human_behavior: {e}")


def collect_slideshows(driver, wait):
    """Collect all slideshows across pagination"""
    slideshows = []
    seen_titles = set()

    while True:
        try:
            wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li a.title"))
            )
        except TimeoutException:
            break

        simulate_human_behavior(driver)

        blocks = driver.find_elements(By.CSS_SELECTOR, "li")
        for block in blocks:
            try:
                title_el = block.find_element(By.CSS_SELECTOR, "a.title")
                title = title_el.text.strip()
                link = title_el.get_attribute("href")
                teaser, date = "", ""

                try:
                    teaser = block.find_element(By.CSS_SELECTOR, "span.teaser").text.strip()
                except:
                    pass
                try:
                    date = block.find_element(By.CSS_SELECTOR, "div.byline").text.strip()
                except:
                    pass

                if title and title not in seen_titles:
                    slideshows.append({
                        "title": title,
                        "link": link,
                        "teaser": teaser,
                        "date": date
                    })
                    seen_titles.add(title)
                    print(f"📌 Collected: {title}")
            except:
                continue

        # pagination
        try:
            try:
                button = driver.find_element(By.CSS_SELECTOR, "a.more")
            except:
                button = driver.find_element(By.XPATH, "//a[text()='Next']")

            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(random.uniform(1, 2))
            driver.execute_script("arguments[0].click();", button)
            print("👉 Clicked pagination button.")
            time.sleep(random.uniform(2, 4))
        except:
            print("✅ No more pages found, finished.")
            break

    return slideshows


def main():
    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')

    try:
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = uc.Chrome(options=options, service=service, use_subprocess=True)
    except Exception as e:
        print(f"⚠️ Error setting up ChromeDriver: {e}")
        return

    driver.maximize_window()

    url = "https://reference.medscape.com/features/slideshow"
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    accept_cookies_if_present(driver, wait)
    remove_cookie_overlay(driver)

    print("⏳ Please log in manually if required. Press ENTER in terminal when done...")
    input()

    slideshows = collect_slideshows(driver, wait)
    print(f"✅ Collected {len(slideshows)} slideshows.")

    # Save CSV
    with open("medscape_slideshows.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "link", "teaser", "date"])
        writer.writeheader()
        for row in slideshows:
            writer.writerow(row)
    print("💾 Data saved to medscape_slideshows.csv")

    # Save JSON
    with open("medscape_slideshows.json", "w", encoding="utf-8") as f:
        json.dump(slideshows, f, indent=4, ensure_ascii=False)
    print("💾 Data saved to medscape_slideshows.json")

    driver.quit()


if __name__ == "__main__":
    main()
