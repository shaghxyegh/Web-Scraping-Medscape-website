import time
import random
import json
import csv
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- Utility functions ----------
def random_delay(a=2, b=5):
    time.sleep(random.uniform(a, b))

def accept_cookies_if_present(driver, wait):
    try:
        cookie_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ccpa-overlay-accept-btn")))
        cookie_button.click()
        print("Accepted cookies.")
        random_delay(2, 3)
    except:
        print("No cookie popup.")

# ---------- Expand All ----------
def expand_all_categories(driver, wait):
    try:
        expand_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.topic-expand")))
        driver.execute_script("arguments[0].scrollIntoView(true);", expand_button)
        random_delay(1, 2)
        expand_button.click()
        print("Clicked 'Expand All'.")
        random_delay(3, 5)
    except Exception as e:
        print("Expand All button not found:", e)

# ---------- Collect links with categories ----------
def collect_procedure_links(driver, wait):
    links_data = []
    seen_urls = set()

    sections = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.topic-section.expanded")))
    for section in sections:
        try:
            category_name = section.find_element(By.CSS_SELECTOR, "div.topic-head").text.strip()

            links = section.find_elements(By.CSS_SELECTOR, "ul li a")
            for a in links:
                title = a.text.strip()
                href = a.get_attribute("href")
                if title and href and "overview" in href and href not in seen_urls:
                    links_data.append({
                        "category": category_name,
                        "title": title,
                        "link": href
                    })
                    seen_urls.add(href)
                    print(f"[{category_name}] {title} - {href}")
        except Exception as e:
            print("Error processing section:", e)
            continue

    return links_data

# ---------- Scrape article ----------
def scrape_article(driver, wait, url):
    article_data = {"content": "", "references": [], "images": []}

    try:
        driver.get(url)
        random_delay(3, 6)

        # Collect text content
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "div.article-section p")
        article_data["content"] = "\n".join([p.text for p in paragraphs if p.text.strip()])

        # Collect references
        refs = driver.find_elements(By.CSS_SELECTOR, "div.article-section.references p")
        article_data["references"] = [r.text for r in refs if r.text.strip()]

        # Collect images
        imgs = driver.find_elements(By.CSS_SELECTOR, "img")
        article_data["images"] = [img.get_attribute("src") for img in imgs if img.get_attribute("src")]

    except Exception as e:
        print(f"Error scraping {url}: {e}")

    return article_data

# ---------- Save Data ----------
def save_data(articles, json_file="procedures_data.json", csv_file="procedures_data.csv"):
    # Save JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

    # Save CSV
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Title", "Link", "Content", "References", "Images"])
        for art in articles:
            writer.writerow([
                art["category"],
                art["title"],
                art["link"],
                art.get("content", "").replace("\n", " "),
                "; ".join(art.get("references", [])),
                "; ".join(art.get("images", []))
            ])

    print(f"Data saved to {json_file} and {csv_file}")

# ---------- Main ----------
def main():
    driver = uc.Chrome()
    wait = WebDriverWait(driver, 20)

    url = "https://emedicine.medscape.com/clinical_procedures"
    driver.get(url)

    accept_cookies_if_present(driver, wait)
    expand_all_categories(driver, wait)

    links_data = collect_procedure_links(driver, wait)
    print(f"Found {len(links_data)} articles.")

    articles = []
    for idx, item in enumerate(links_data, 1):
        print(f"Scraping {idx}/{len(links_data)}: {item['title']}")
        data = scrape_article(driver, wait, item["link"])
        item.update(data)
        articles.append(item)
        random_delay(4, 7)

    save_data(articles)

    driver.quit()

if __name__ == "__main__":
    main()
