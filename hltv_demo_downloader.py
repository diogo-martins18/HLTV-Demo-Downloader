from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (WebDriverException, NoSuchElementException, TimeoutException)
from urllib.parse import urlparse
import time
from pathlib import Path

def main():
    print("*** HLTV DEMO DOWNLOADER ***")

    while True:
        stat_page_link = input("Enter the stats page link: ")
        if is_valid_url(stat_page_link):
            break
        else:
            print("[ERROR] Incorrect link format.")

    folder_input = input("Enter the download folder path: ").strip()
    if not folder_input:
        default_path = Path.cwd() / "downloads"
        print(f"[!!!] No folder provided. Using default: {default_path}")
        folder_path = default_path
    else:
        folder_path = Path(folder_input).expanduser().resolve()

    folder_path.mkdir(parents=True, exist_ok=True)
    folder_path=str(folder_path)
    
    match_links = get_matches(stat_page_link, folder_path)
    failed_links = []

    total_links = len(match_links)
    for index, link in enumerate(match_links, start=1): 
        progress = f"({index}/{total_links})"
        try:
            get_demo(link, progress, folder_path)
        except DemoDownloadError as e:
            print(f"[ERROR] {str(e)}")
            failed_links.append(link)
            continue
        except Exception as e:
            print(f"[ERROR] An unexpected error has occurred: {str(e)}")
            failed_links.append(link)
            continue
        print(f"*** Download completed ***")

    success_count = total_links - len(failed_links)
    print(f"\n*** Finished: {success_count} of {total_links} demos downloaded successfully ***")
    if success_count != total_links:
        print(f"URL of failed links:")
        for i, link in enumerate(failed_links, start=1): print(f"{i} : URL: {link}")


def get_matches(stat_page_link, folder_path):
    print("Fetching match pages...")
    driver = firefox_driver(folder_path)
    driver.get(stat_page_link)

    # Decline the cookies pop-up
    cookies = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "CybotCookiebotDialogBodyButtonDecline")))
    cookies.click()

    match_links = []
    is_last_page = False
    while is_last_page == False:
        # Find matches with the dark background in this page (html match rectangle)
        elements2 = driver.find_elements(By.CSS_SELECTOR, ".group-2.first")
        
        # Find matches with a grey background in this page
        elements1 = driver.find_elements(By.CSS_SELECTOR, ".group-1.first")

        for i in range(min(len(elements2), len(elements1))):
            link2 = elements2[i].find_element(By.TAG_NAME, "a").get_attribute("href")
            match_links.append(link2.split('?')[0])

            link1 = elements1[i].find_element(By.TAG_NAME, "a").get_attribute("href")
            match_links.append(link1.split('?')[0])
        
        if len(elements2) > len(elements1):
            link2 = elements2[len(elements2) - 1].find_element(By.TAG_NAME, "a").get_attribute("href")
            match_links.append(link2.split('?')[0])

        # Go to the next page if there are more matches left
        try: 
            next_page = driver.find_element(By.CSS_SELECTOR, ".pagination-next")
            if next_page.get_attribute("href"):
                next_page.click()
            else:
                is_last_page = True
        except NoSuchElementException:
            is_last_page = True
    
    for link in match_links:
        print(link)
    print(f"Found {len(match_links)} demos.")

    driver.quit()
    return match_links

class DemoDownloadError(Exception):
    """Custom exception for demo download errors"""
    pass

def get_demo(match_page: str, progress_number: int, folder_path: str):
    driver = firefox_driver(folder_path)
    try:
        driver.get(match_page)
        _handle_cookies(driver)
        _navigate_to_match_page(driver)
        download_button = _get_download_button(driver)
        _execute_download(progress_number, match_page, download_button, folder_path)
    finally:
        driver.quit()

# Auxiliary (modularized) functions
def _handle_cookies(driver):
    try:
        cookies = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline")))
        cookies.click()
    except TimeoutException:
        print("[INFO] Cookie banner not found")

def _navigate_to_match_page(driver):
    try:
        matchpage = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "More info on match page")))
        matchpage.click()
    except TimeoutException:
        raise DemoDownloadError("Match page link not found")

def _get_download_button(driver):
    try:
        return WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Demo sponsored by Bitskins")))
    except TimeoutException:
        raise DemoDownloadError("Download button not found - demo unavailable")

def _execute_download(progress_number, match_page, download_btn, folder_path):
    rename_old_part(folder_path)

    print(f"\n*** {progress_number} Demo download ***")
    print(f"Link: {match_page}")

    download_btn.click()
    time.sleep(5)

    try:
        part_file = wait_for_new_part(folder_path)
    except TimeoutException:
        raise DemoDownloadError(".part file not detected")
    
    if is_downloading(part_file):
        raise DemoDownloadError("Download stuck without progress")


#Waits for any visible .part, returns the most recent.
def wait_for_new_part(folder, timeout_appear=30):
    start = time.time()
    latest = None
    latest_time = 0

    while time.time() - start < timeout_appear:
        parts = list(Path(folder).glob("*.part"))
        if parts:
            newest = max(parts, key=lambda p: p.stat().st_mtime)
            mod_time = newest.stat().st_mtime

            if mod_time > latest_time:
                latest = newest
                latest_time = mod_time
                break

        time.sleep(1)

    if latest:
        return latest
    raise TimeoutError("Theres no .part in the folder")


# In case there are already .part files in the download folder 
# this will rename the files to avoid conflicts
def rename_old_part(folder):
    for p in Path(folder).glob("*.part"):
        target = p.with_suffix(".part.old")
        index= 1
        while target.exists():
            target = p.with_suffix(f".part.old{index}")
            index += 1
        print(f"Renaming {p.name} → {target.name}")
        p.rename(target)


def is_downloading(part_path, timeout_stall=300, check=5):
    last_size = -1
    last_change = time.time()

    while part_path.exists():
        size = part_path.stat().st_size
        if size != last_size:
            last_size = size
            last_change = time.time()
            print("Downloading...")
        elif time.time() - last_change > timeout_stall:
            return True

        time.sleep(check)
    return False


def is_valid_url(url):
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc]) and "https://www.hltv.org/stats/" in url


def firefox_driver(folder_path):
    options = webdriver.FirefoxOptions()
    #SETTINGS TO AVOID CONFIRMATION POPUPS  
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.manager.quitBehavior", 2)  # 0=default, 1=cancel, 2=continue
    options.set_preference("browser.download.manager.showAlertOnComplete", False)
    options.set_preference("browser.download.manager.focusWhenStarting", False)    
    
    options.add_argument("-headless")
    options.set_preference("browser.download.folderList", 2) 
    options.set_preference("browser.download.dir", folder_path)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/x-rar-compressed") 
    driver = webdriver.Firefox(options=options) 
    return driver


if __name__  == "__main__":
	main()
