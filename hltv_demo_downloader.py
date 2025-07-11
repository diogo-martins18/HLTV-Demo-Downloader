from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def main():
    print("*** HLTV DEMO DOWNLOADER ***")
    link = input("Enter the player match link: ")
    folder_path = input("Enter the download folder path: ")


    # Get an array with links to the matchpages
    match_links = get_matches(link, folder_path)
    print(f"Found {len(match_links)} demos.")
    print("Starting to download...\n")
 
    # Start downloading all the demos 1 by 1
    for index, link in enumerate(match_links, start=1):
        progress = f"({index}/{len(match_links)})"
        get_demo(link, progress, folder_path)

    print("*** All demos have been downloaded successfully ***")


def get_matches(player_page, folder_path):
    print("Fetching match pages...")

    driver = firefox_driver(folder_path)

    driver.get(player_page)
    time.sleep(3)


    match_links = []

    elements2 = driver.find_elements(By.CSS_SELECTOR, ".group-2.first")
    elements1 = driver.find_elements(By.CSS_SELECTOR, ".group-1.first")

    for i in range(min(len(elements2), len(elements1))):
        link2 = elements2[i].find_element(By.TAG_NAME, "a").get_attribute("href")
        match_links.append(link2.split('?')[0])

        link1 = elements1[i].find_element(By.TAG_NAME, "a").get_attribute("href")
        match_links.append(link1.split('?')[0])


    for link in match_links:
        print(link)

    driver.quit()
    return match_links


def get_demo(match_page, progress_number, folder_path):

    driver = firefox_driver(folder_path)

    driver.get(match_page)

    try:
        # Click the cookies pop-up
        cookies = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "CybotCookiebotDialogBodyButtonDecline")))
        cookies.click()

        # Get to the matchpage
        matchpage = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.PARTIAL_LINK_TEXT, "More info on match page")
        ))
        matchpage.click()

        # Click to the download button
        download_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (By.PARTIAL_LINK_TEXT, "Demo sponsored by Bitskins")
        ))
        print(f"*** {progress_number} Demo download ***")
        print("Link of the demo being downloaded: " + match_page)
        download_btn.click()

        time.sleep(10)

        while is_downloading(folder_path):
            print("Downloading file...")
            time.sleep(5)
    finally:
        print("*** File downloaded successfully ***\n")
        driver.quit()


def firefox_driver(folder_path):
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", folder_path)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/x-rar-compressed")
    driver = webdriver.Firefox(options=options)
    return driver


def is_downloading(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith('.part'):
            return True
    return False


def next_page(match_page, folder_path):
    driver = firefox_driver(folder_path)
    driver.get(match_page)
    
    cookies = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "CybotCookiebotDialogBodyButtonDecline")))
    cookies.click()

    next_page = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "pagination-next ")))
    next_page.click()


if __name__  == "__main__":
	main()

