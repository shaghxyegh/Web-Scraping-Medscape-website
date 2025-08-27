import json
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

INPUT_FILE = "medscape_slideshows.json"
OUTPUT_FILE = "slideshows_with_slides.json"
MAX_RETRIES = 3

CHROME_PROFILE_PATH = r"C:\Users\Mandegar\AppData\Local\Google\Chrome\User Data\Default"
PROFILE_DIRECTORY = "Default"

def extract_slides(driver):
    slides = []
    last_heading = None
    last_page_num = None

    while True:
        try:
            # Wait for slide heading
            heading_el = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "h1.crs-header__title, h2.crs-header__title"))
            )
            heading = heading_el.text.strip()

            # Current page number
            try:
                page_el = driver.find_element(By.CSS_SELECTOR, "span.crs-pagination_current")
                page_num = int(page_el.text.strip())
            except:
                page_num = None

            # Stop if duplicate slide/page
            if heading == last_heading and page_num == last_page_num:
                break
            last_heading = heading
            last_page_num = page_num

            # Extract image
            try:
                img_el = driver.find_element(By.CSS_SELECTOR, "figure img.crs-slide_image")
                image_url = img_el.get_attribute("src")
            except NoSuchElementException:
                image_url = ""

            # Extract caption
            try:
                caption_el = driver.find_element(By.CSS_SELECTOR, "figure figcaption cite.crs-slide_credit")
                caption = caption_el.text.strip()
            except NoSuchElementException:
                caption = ""

            # Extract text
            try:
                paras = driver.find_elements(By.CSS_SELECTOR, "div.crs-slide__copy p")
                text = " ".join([p.text.strip() for p in paras if p.text.strip()])
            except NoSuchElementException:
                text = ""

            slides.append({
                "heading": heading,
                "image_url": image_url,
                "caption": caption,
                "text": text
            })

            # Top pagination forward button
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.crs-pagination a.crs_nav_arrow--forward"))
                )
                if next_button.get_attribute("aria-disabled") == "true":
                    break

                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_button)
                time.sleep(random.uniform(0.5, 1.5))
                try:
                    next_button.click()
                except StaleElementReferenceException:
                    next_button = driver.find_element(By.CSS_SELECTOR, "div.crs-pagination a.crs_nav_arrow--forward")
                    next_button.click()

                # Wait for new heading or page number
                WebDriverWait(driver, 15).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "h1.crs-header__title, h2.crs-header__title").text.strip() != heading
                    or int(d.find_element(By.CSS_SELECTOR, "span.crs-pagination_current").text.strip()) != page_num
                )
                time.sleep(random.uniform(1, 2))

            except (NoSuchElementException, TimeoutException):
                break

        except TimeoutException:
            print("⚠️ Timeout waiting for slide content")
            break

    return slides

def save_progress(results):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

def main():
    # Load JSON
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        slideshows = json.load(f)

    # Fix malformed links
    for show in slideshows:
        if "comslideshow" in show["link"]:
            show["link"] = show["link"].replace("comslideshow", "com/slideshow")

    # Overwrite old output to start fresh
    results = []

    # Setup Chrome
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}")
    options.add_argument(f"--profile-directory={PROFILE_DIRECTORY}")
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)

    for show in slideshows:
        retries = 0
        while retries < MAX_RETRIES:
            try:
                url = show["link"]
                print(f"🔗 Opening: {url}")
                driver.get(url)

                WebDriverWait(driver, 20).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "h1.crs-header__title, h2.crs-header__title"))
                )

                slides = extract_slides(driver)
                show["slides"] = slides
                results.append(show)
                save_progress(results)
                print(f"✅ Extracted {len(slides)} slides from {show['title']}")
                break

            except TimeoutException:
                retries += 1
                print(f"⚠️ Timeout on {show['title']}, retry {retries}/{MAX_RETRIES}")
                time.sleep(random.uniform(3, 6))

    driver.quit()
    print(f"🎉 Finished! Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
