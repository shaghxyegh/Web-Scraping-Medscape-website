import json
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Load JSON file with article links
with open("medscape_simulation.json", "r", encoding="utf-8") as f:
    articles_list = json.load(f)

def close_popups(driver, wait):
    """Close pop-ups if present"""
    try:
        close_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Close Patient Chart'], .popup-close, .modal-close"))
        )
        close_btn.click()
        time.sleep(1)
        print("✅ Closed popup.")
    except TimeoutException:
        pass

def get_section_content(section):
    """Extract text or table from a section"""
    try:
        title_elem = section.find_element(By.CSS_SELECTOR, ".info-title, .info-subtitle")
        title = title_elem.text.strip()
        if "Tests" in title:
            return None, None
    except NoSuchElementException:
        return None, None

    # Try extracting table first
    try:
        table = section.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")
        if not rows:
            return title, None
        headers = [th.text.strip() for th in rows[0].find_elements(By.TAG_NAME, "th")]
        table_data = []
        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) != len(headers):
                # Skip malformed rows
                continue
            row_data = {headers[i]: cells[i].text.strip() for i in range(len(cells))}
            table_data.append(row_data)
        if table_data:
            return title, table_data
        else:
            # Table exists but empty, fallback to paragraphs
            raise NoSuchElementException
    except NoSuchElementException:
        # Extract paragraphs
        paragraphs = section.find_elements(By.TAG_NAME, "p")
        text = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
        if text:
            return title, text
        return None, None


def scrape_article(driver, article):
    driver.get(article['link'])
    time.sleep(random.uniform(2, 4))

    wait = WebDriverWait(driver, 10)
    close_popups(driver, wait)

    content = {}

    # Right sections
    try:
        right_sections = driver.find_elements(By.CSS_SELECTOR, ".info-section.css-1i2ky5l")
        for section in right_sections:
            title, data = get_section_content(section)
            if title and data:
                content[title] = data
    except Exception as e:
        print(f"⚠️ Error scraping right section: {e}")

    # Left sections
    try:
        left_sections = driver.find_elements(By.CSS_SELECTOR, ".chart-content .info-section")
        for section in left_sections:
            title, data = get_section_content(section)
            if title and data:
                content[title] = data
    except Exception as e:
        print(f"⚠️ Error scraping left section: {e}")

    article_data = article.copy()
    article_data['content'] = content
    return article_data

def main():
    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    driver = uc.Chrome(options=options)
    driver.maximize_window()

    print("⏳ Please log in manually and complete human verification. Press ENTER here when done...")
    input()

    scraped_articles = []
    for idx, article in enumerate(articles_list, 1):
        print(f"⏳ Scraping article {idx}/{len(articles_list)}: {article['title']}")
        try:
            data = scrape_article(driver, article)
            scraped_articles.append(data)
        except Exception as e:
            print(f"⚠️ Failed to scrape {article['link']}: {e}")
        time.sleep(random.uniform(2, 4))  # small delay between requests

    # Save JSON
    with open("medscape_simulations_detail.json", "w", encoding="utf-8") as f:
        json.dump(scraped_articles, f, indent=4, ensure_ascii=False)

    driver.quit()
    print("✅ Scraping complete! Data saved to scraped_articles.json")

if __name__ == "__main__":
    main()
