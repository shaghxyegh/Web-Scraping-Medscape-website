from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import csv
import time
import random
import undetected_chromedriver as uc
import traceback
import json


def accept_cookies_if_present(driver, wait):
    try:
        accept_button = wait.until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        accept_button.click()
        print("Clicked on 'I Accept' cookie button.")
        time.sleep(1)
    except TimeoutException:
        print("No cookie consent popup found or button not clickable.")


def remove_cookie_overlay(driver):
    try:
        overlay = driver.find_element(By.CSS_SELECTOR, ".onetrust-pc-dark-filter")
        driver.execute_script("arguments[0].style.display = 'none';", overlay)
        print("Removed cookie overlay.")
    except Exception:
        print("No cookie overlay found or could not remove.")


def simulate_human_behavior(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 3))
        action = ActionChains(driver)
        action.move_by_offset(random.randint(10, 100), random.randint(10, 100)).perform()
        time.sleep(random.uniform(0.5, 2))
        print("Simulated human behavior")
    except Exception as e:
        print(f"Error simulating human behavior: {e}")


def _dedup_preserve(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_anatomy_content(driver, wait):
    try:
        # Click "Show All" if present
        try:
            show_all_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Show All")))
            driver.execute_script("arguments[0].click();", show_all_link)
            time.sleep(random.uniform(2, 4))
        except TimeoutException:
            print("'Show All' not found, continuing...")

        all_text = []
        content_divs = driver.find_elements(By.CLASS_NAME, "refsection_content")
        for div in content_divs:
            for element in div.find_elements(
                By.XPATH,
                ".//*[self::p or self::h2 or self::ul or self::li or self::h3]"
                "[not(contains(@class, 'AdUnit') or contains(@id, 'ads-pos-'))]"
            ):
                text = element.text.strip()
                if text:
                    all_text.append(text)
        return "\n".join(all_text) if all_text else ""
    except Exception as e:
        print(f"Error extracting anatomy content: {e}")
        return ""


def extract_images(driver):
    """Collect inline image URLs under div.inlineImage, normalize protocol, and de-duplicate."""
    try:
        images = driver.find_elements(By.CSS_SELECTOR, "div.inlineImage img")
        image_links = []
        for img in images:
            src = img.get_attribute("src")
            if src and src.startswith("//"):
                src = "https:" + src
            if src:
                image_links.append(src)
        return _dedup_preserve(image_links)
    except Exception as e:
        print(f"Error extracting images: {e}")
        return []


def _extract_references_from_modal(driver, wait):
    """Open the References modal and scrape all <p> citations + any links inside them."""
    refs = []
    try:
        # Try clicking the References link if present
        try:
            ref_link = driver.find_element(
                By.XPATH,
                "//a[contains(@href, \"showModal('references-layer')\") or normalize-space()='References']"
            )
            driver.execute_script("arguments[0].click();", ref_link)
        except Exception:
            # Fall back to executing the page function directly
            try:
                driver.execute_script("if (typeof showModal === 'function') { showModal('references-layer'); }")
            except Exception:
                pass

        # Wait for the modal to be visible
        modal = wait.until(EC.visibility_of_element_located((By.ID, "references-layer")))

        # Grab every paragraph in the modal (each is a citation block)
        p_nodes = modal.find_elements(By.CSS_SELECTOR, "p")
        for p in p_nodes:
            citation = p.text.strip()
            if not citation:
                continue
            urls = []
            for a in p.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href")
                if href:
                    urls.append(href)
            refs.append({"citation": citation, "urls": _dedup_preserve(urls)})

    except TimeoutException:
        print("References modal not found or not visible.")
    except Exception as e:
        print(f"Error extracting references from modal: {e}")
    finally:
        # Try to close/hide the modal to keep the DOM clean
        try:
            driver.execute_script(
                "if (typeof hideModal === 'function') { hideModal('references-layer'); }"
                "else { var m = document.getElementById('references-layer'); if (m) { m.style.display='none'; } }"
            )
        except Exception:
            pass
    return refs


def _extract_inline_references_tooltips(driver):
    """Fallback: scrape hidden tooltip citations embedded in the article body (if any)."""
    refs = []
    try:
        anchors = driver.find_elements(By.CSS_SELECTOR, "a.tooltip_link")
        for a in anchors:
            for p in a.find_elements(By.CSS_SELECTOR, "div.tooltip p"):
                txt = p.text.strip()
                if not txt:
                    continue
                urls = []
                for link in p.find_elements(By.TAG_NAME, "a"):
                    href = link.get_attribute("href")
                    if href:
                        urls.append(href)
                refs.append({"citation": txt, "urls": _dedup_preserve(urls)})
    except Exception as e:
        print(f"Error extracting inline tooltip references: {e}")
    return refs


def extract_references(driver, wait):
    """Primary: modal-based refs. Fallback: inline tooltip refs."""
    refs = _extract_references_from_modal(driver, wait)
    if not refs:
        refs = _extract_inline_references_tooltips(driver)
    return refs


def main():
    options = uc.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    driver = uc.Chrome(options=options, version_main=138)  # Adjust to your Chrome version
    driver.maximize_window()

    url = "https://reference.medscape.com/guide/anatomy"
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    accept_cookies_if_present(driver, wait)
    simulate_human_behavior(driver)

    # Collect article links
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/article/']")))
        article_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/article/']")
        links_data = []
        seen_urls = set()
        for el in article_elements:
            try:
                title = el.text.strip()
                href = el.get_attribute("href")
                if title and href and "overview" in href and href not in seen_urls:
                    links_data.append({"title": title, "link": href})
                    seen_urls.add(href)
                    print(f"Collected: {title} - {href}")
            except Exception as e:
                print(f"Error processing element: {e}")
                continue
    except TimeoutException:
        print("No article links found.")
        links_data = []

    print(f"Found {len(links_data)} articles.")

    all_data = []
    for idx, item in enumerate(links_data):
        title = item["title"]
        link = item["link"]
        print(f"Processing article {idx+1}/{len(links_data)}: {title}")
        try:
            driver.get(link)
            accept_cookies_if_present(driver, wait)
            remove_cookie_overlay(driver)
            simulate_human_behavior(driver)

            article_data = {
                "title": title,
                "link": link,
                "Anatomy": "",
                "Images": [],
                "References": []  # list of {"citation": ..., "urls": [...]}
            }

            # Extract content
            content = extract_anatomy_content(driver, wait)
            images = extract_images(driver)
            references = extract_references(driver, wait)

            article_data["Anatomy"] = content
            article_data["Images"] = images
            article_data["References"] = references

            print(f"Extracted Anatomy, Images, and References for {title}")

            all_data.append(article_data)

            # ------- Persist after each article (JSON = source of truth) -------
            # Save JSON (structured)
            with open("anatomy_articles.json", "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=4)

            # Save CSV (flattened for spreadsheet viewing)
            with open("anatomy_articles.csv", "w", encoding="utf-8", newline="") as f:
                fieldnames = ["title", "link", "Anatomy", "Images", "References", "ReferenceURLs"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in all_data:
                    flat_citations = " || ".join([r["citation"] for r in row.get("References", [])])
                    # flatten all URLs from all references
                    all_urls = []
                    for r in row.get("References", []):
                        all_urls.extend(r.get("urls", []))
                    flat_urls = " ; ".join(_dedup_preserve(all_urls))
                    writer.writerow({
                        "title": row["title"],
                        "link": row["link"],
                        "Anatomy": row["Anatomy"],
                        "Images": " ; ".join(row["Images"]),
                        "References": flat_citations,
                        "ReferenceURLs": flat_urls
                    })

            print(f"Saved data for {title}")
            time.sleep(random.uniform(2, 5))
            driver.get(url)
            accept_cookies_if_present(driver, wait)
            remove_cookie_overlay(driver)
            simulate_human_behavior(driver)
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"Error processing {link}: {e}")
            print(f"Stack trace: {traceback.format_exc()}")
            continue

    print("Finished processing all articles.")
    driver.quit()


if __name__ == "__main__":
    main()
