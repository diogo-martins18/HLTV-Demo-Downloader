from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
from pathlib import Path
import time
import os


def main():
    print("*** HLTV DEMO DOWNLOADER ***")

    stat_page_link = get_valid_stat_page_url()
    download_folder = os.getcwd() + "/download"

    print("Fetching match pages...")
    match_page_links = get_matches(stat_page_link)

    for link in match_page_links:
        print(link)
    print(f"Found {len(match_page_links)} demos.")

    download_all_demos(match_page_links, download_folder)


def get_matches(stat_page_link: str) -> list:
    """
    Returns a list of match page links that are present in the stat page link

    :param stat_page_link: Stat page URL
    :return: A list of match page links that are present in the stat page link
    """

    driver = firefox_driver()
    driver.get(stat_page_link)

    # Decline the cookies pop-up
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
    ).click()

    match_page_links = []
    is_last_page = False
    while not is_last_page:
        # Find matches with the dark background in this page (html match rectangle)
        elements2 = driver.find_elements(By.CSS_SELECTOR, ".group-2.first")

        # Find matches with a grey background in this page
        elements1 = driver.find_elements(By.CSS_SELECTOR, ".group-1.first")

        for i in range(min(len(elements2), len(elements1))):
            link2 = elements2[i].find_element(By.TAG_NAME, "a").get_attribute("href")
            link1 = elements1[i].find_element(By.TAG_NAME, "a").get_attribute("href")

            if link1 and link2:
                match_page_links.append(link2.split("?")[0])
                match_page_links.append(link1.split("?")[0])

        if len(elements2) > len(elements1):
            link2 = (
                elements2[len(elements2) - 1]
                .find_element(By.TAG_NAME, "a")
                .get_attribute("href")
            )
            if link2:
                match_page_links.append(link2.split("?")[0])

        # Go to the next page if there are more matches left
        try:
            next_page = driver.find_element(By.CSS_SELECTOR, ".pagination-next")
            if next_page.get_attribute("href"):
                next_page.click()
            else:
                is_last_page = True
        except NoSuchElementException:
            is_last_page = True

    driver.quit()
    return match_page_links


def download_all_demos(match_page_links: list, download_folder: str):
    """
    Goes through all the match pages and downloads all the demos.

    :param match_page_links: A list of match page links.
    :download_folder: The path to the folder where the demos will be downloaded to.
    """

    driver = firefox_driver(download_folder)
    rename_part_files(download_folder)

    failed_links = []
    num_of_matches = len(match_page_links)
    for index, link in enumerate(match_page_links, start=1):
        print(f"\n*** ({index}/{num_of_matches}) Demo download ***")
        print(f"Link: {link}")
        try:
            download_demo(link, driver, download_folder)
            print(f"*** Download completed ***")
        except Exception as e:
            print(f"[ERROR]: {str(e)}")
            failed_links.append(link)
            continue

    driver.quit()
    success_count = num_of_matches - len(failed_links)
    print(
        f"\n*** Finished: {success_count} of {num_of_matches} demos downloaded successfully ***"
    )

    if success_count != num_of_matches:
        print(f"URL of failed links:")
        for i, link in enumerate(failed_links, start=1):
            print(f"{i}: {link}")


def download_demo(match_page_url: str, driver, download_folder: str):
    """
    Downloads a demo from a matchpage.

    :param match_page_url: Match page URL.
    :download_folder: The path to the folder where the demos will be downloaded to.
    """

    driver.get(match_page_url)

    # Decline cookies
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
        ).click()
    except:
        pass

    # Get to the matchpage
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "More info on match page"))
    ).click()

    try:
        # Click the download button
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Demo sponsored by Bitskins"))
        ).click()
    except:
        raise RuntimeError("Demo isn't available")

    part_file = get_part_file(download_folder)
    if part_file == None:
        raise RuntimeError("Download didn't start")

    if not downloaded_sucessfully(part_file):
        raise RuntimeError("Download stuck without progress")


def get_part_file(folder: str, timeout_appear=30):
    """
    Waits for any visible .part and returns the most recent one.

    :param folder: The path of the folder being searched.
    :param timeout_appear: Time that the function will search the folder before it gives up.

    :return: The path of the most recent .part file, or None if none are found.
    """

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
    return latest


def downloaded_sucessfully(part_file, timeout=5) -> bool:
    """
    Checks if a file downloaded sucessfully being checking if the .part is growing in size over time.

    :param part_file: .part file of the file being downloaded.
    :param timeout: Time between size checks.

    :return: True if the .part file disappeared, False if the file doesn't change size over time.
    """

    old_size = -1

    while part_file.exists():
        current_size = part_file.stat().st_size
        if current_size != old_size:
            old_size = current_size
            print("Downloading...")
        else:
            return False

        time.sleep(timeout)
    return True


def rename_part_files(folder: str):
    """
    Renames existing .part files in the folder to avoid conflicts.

    :param folder: Path of the folder where the .part files could be.
    """
    for file in Path(folder).glob("*.part"):
        target = file.with_suffix(".part.old")
        index = 1
        while target.exists():
            target = file.with_suffix(f".part.old{index}")
            index += 1
        print(f"Renaming {file.name} → {target.name}")
        file.rename(target)


def get_valid_stat_page_url() -> str:
    """
    Keeps prompting the user for a valid HLTV stat page URL.

    :return: The url if it's valid.
    """
    while True:
        stat_page_link = input("Enter the stats page link: ")
        if is_valid_url(stat_page_link):
            return stat_page_link
        else:
            print("[ERROR] Incorrect link format.")


def is_valid_url(url) -> bool:
    """
    Checks if a string is a valid HLTV stat page URL.

    :param url: The string being checked.
    :return: True if the string is a valid HLTV stat page URL.
    """

    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc]) and "https://www.hltv.org/stats/" in url


def firefox_driver(download_folder=None):
    """
    Returns a driver for an automated firefox browser being controlled by Selenium.

    :download_folder: The path to the folder where files will be downloaded to.
    :return: A driver for an automated firefox browser being controlled by Selenium.
    """

    options = webdriver.FirefoxOptions()

    if download_folder:
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", download_folder)
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk", "application/x-rar-compressed"
        )

    options.add_argument("-headless")
    return webdriver.Firefox(options=options)


if __name__ == "__main__":
    main()
