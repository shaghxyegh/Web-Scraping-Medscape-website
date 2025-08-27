import csv
import json
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


def accept_cookies_if_present(driver, wait):
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
    try:
        overlay = driver.find_element(By.CSS_SELECTOR, ".onetrust-pc-dark-filter")
        driver.execute_script("arguments[0].style.display = 'none';", overlay)
        print("✅ Removed cookie overlay.")
    except Exception:
        pass


def simulate_human_behavior(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 3))
    except Exception as e:
        print(f"⚠️ Error in simulate_human_behavior: {e}")


def collect_questions(driver, wait, calculator_url):
    try:
        driver.get(calculator_url)
        time.sleep(random.uniform(2, 4))
        remove_cookie_overlay(driver)

        questions = []
        try:
            question_elements = wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.ListItems__Wrapper-sc-10zkkk4-1 a.QuestionListItem__Root-sc-8dcub9-0")
                )
            )
            for q in question_elements:
                question_text = q.find_element(By.CSS_SELECTOR,
                                               "div.QuestionListItem__Section-sc-8dcub9-1 span:last-child").text.strip()
                if question_text:
                    questions.append(question_text)
                    print(f"    ❓ Collected question: {question_text}")
        except TimeoutException:
            print(f"⚠️ No questions found for {calculator_url}")
        return questions
    except Exception as e:
        print(f"⚠️ Error collecting questions for {calculator_url}: {e}")
        return []


def collect_all_calculator_links(driver, wait):
    links_data = []
    seen_urls = set()

    # Retry logic for category expansion
    def try_click(element, description, retries=3):
        for attempt in range(retries):
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(random.uniform(0.5, 1.5))
                driver.execute_script("arguments[0].click();", element)
                time.sleep(random.uniform(1, 2))
                return True
            except (StaleElementReferenceException, TimeoutException) as e:
                print(f"⚠️ Retry {attempt + 1}/{retries} for {description}: {e}")
                time.sleep(1)
        return False

    # Get all categories
    categories = driver.find_elements(By.CSS_SELECTOR, "div.topic-head")
    print(f"Found {len(categories)} categories.")

    for i, cat in enumerate(categories):
        try:
            category_name = cat.text.strip()
            print(f"Processing category: {category_name}")

            # Expand category
            if not try_click(cat, f"category {category_name}"):
                print(f"⚠️ Failed to expand category {category_name} after retries.")
                continue

            # Find subsections within the category
            subsections = cat.find_elements(By.XPATH, "./following-sibling::div[contains(@class, 'topic-subsection')]")
            for sub in subsections:
                try:
                    # Get subsection name
                    subhead = sub.find_element(By.CSS_SELECTOR, "div.topic-subhead")
                    subsection_name = subhead.text.strip()

                    # Expand subsection
                    if not try_click(subhead, f"subsection {subsection_name}"):
                        print(f"⚠️ Failed to expand subsection {subsection_name} after retries.")
                        continue

                    # Collect links under subsection
                    sub_links = sub.find_elements(By.CSS_SELECTOR, "ul a")
                    for a in sub_links:
                        try:
                            title = a.text.strip()
                            href = a.get_attribute("href")
                            if title and href and href not in seen_urls:
                                if not href.startswith("http"):
                                    href = "https://reference.medscape.com" + href
                                links_data.append({
                                    "category": category_name,
                                    "subcategory": subsection_name,
                                    "title": title,
                                    "link": href,
                                    "questions": []  # Questions will be filled later
                                })
                                seen_urls.add(href)
                                print(f"🔗 Collected: {category_name} > {subsection_name} > {title} - {href}")
                        except Exception as e:
                            print(f"⚠️ Error processing link in {category_name} > {subsection_name}: {e}")
                            continue

                except Exception as e:
                    print(f"⚠️ Error processing subsection under {category_name}: {e}")
                    continue

            # Collect links directly under category (not in a subsection)
            direct_links = cat.find_elements(By.XPATH,
                                             "./following-sibling::ul[not(preceding-sibling::div[contains(@class, 'topic-subsection')])]/li/a")
            for a in direct_links:
                try:
                    title = a.text.strip()
                    href = a.get_attribute("href")
                    if title and href and href not in seen_urls:
                        if not href.startswith("http"):
                            href = "https://reference.medscape.com" + href
                        links_data.append({
                            "category": category_name,
                            "subcategory": "",
                            "title": title,
                            "link": href,
                            "questions": []  # Questions will be filled later
                        })
                        seen_urls.add(href)
                        print(f"🔗 Collected: {category_name} > {title} - {href}")
                except Exception as e:
                    print(f"⚠️ Error processing direct link in {category_name}: {e}")
                    continue

        except Exception as e:
            print(f"⚠️ Error processing category {category_name}: {e}")
            continue

    return links_data


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

    url = "https://reference.medscape.com/guide/medical-calculators"
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    accept_cookies_if_present(driver, wait)
    remove_cookie_overlay(driver)
    simulate_human_behavior(driver)

    # Step 1: Collect all calculator links
    print("Collecting all calculator links...")
    links_data = collect_all_calculator_links(driver, wait)
    print(f"✅ Collected {len(links_data)} calculator links.")

    # Step 2: Collect questions for each calculator
    print("Collecting questions for each calculator...")
    for i, item in enumerate(links_data):
        print(f"Processing calculator {i + 1}/{len(links_data)}: {item['title']}")
        questions = collect_questions(driver, wait, item['link'])
        item['questions'] = questions
        print(f"✅ Collected {len(questions)} questions for {item['title']}")

    # Save CSV
    with open("medscape_calculators.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "subcategory", "title", "link", "questions"])
        writer.writeheader()
        for row in links_data:
            row["questions"] = "; ".join(row["questions"])  # Join questions for CSV
            writer.writerow(row)
    print("💾 Data saved to medscape_calculators.csv")

    # Save JSON
    with open("medscape_calculators.json", "w", encoding="utf-8") as f:
        json.dump(links_data, f, indent=4, ensure_ascii=False)
    print("💾 Data saved to medscape_calculators.json")

    driver.quit()


if __name__ == "__main__":
    main()