from flask import Flask, request, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
from threading import Thread
from collections import deque
import time
import os


table = []
match_links = []
changes_queue = deque()
keep_downloading = True


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST": 
        link = request.form['content']
        download_folder = os.getcwd() + "/download"

        global match_links
        match_links = get_matches(link, download_folder)

        global table
        for link in match_links:
            table.append({"link": link, "status": "pending"})
            print(table)

        return redirect(url_for('downloading'))
    else:
        return render_template("index.html")
    

@app.route("/stop_task")
def stop_and_redirect():
    global keep_downloading
    keep_downloading = False
    
    global table
    table = []

    global match_links
    match_links = []

    return redirect(url_for("index")) 


@app.route('/downloading')
def downloading():
    global changes_queue
    changes_queue = deque()
    
    thread = Thread(target=download_all_demos, args=(match_links,))
    thread.daemon = True
    thread.start()
    return render_template("downloading.html", table=table)



def download_all_demos(match_links):
    download_folder = os.getcwd() + "/download"
    num_of_matches = len(match_links)
    driver = firefox_driver(download_folder)

    global changes_queue

    global keep_downloading
    keep_downloading = True
    
    index = 0
    while keep_downloading and index < len(match_links):
        link = match_links[index]

        changes_queue.append([index+1, "Downloading"])

        try:
            driver.get(link)
            if index == 0:
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
            print(f"*** ({index+1}/{num_of_matches}) Demo download ***")
            print("Link of the demo being downloaded: " + link)
            download_btn.click()

            time.sleep(10)

            while is_downloading(download_folder):
                print("Downloading file...")
                time.sleep(5)
            
            changes_queue.append([index+1, 'Completed'])
        except:
            changes_queue.append([index+1, 'Failed'])
        finally:
            index += 1
            print("*** File downloaded successfully ***\n")
    driver.quit()


@socketio.on('request_update')
def handle_request():
    if changes_queue:
        print(changes_queue)
        changes = changes_queue.popleft()
        emit('update_element', changes)        
     

def get_matches(stat_page_link, folder_path):
    print("Fetching match pages...")
    driver = firefox_driver(folder_path)
    driver.get(stat_page_link)

    # Click the cookies pop-up
    cookies = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "CybotCookiebotDialogBodyButtonDecline")))
    cookies.click()

    match_links = []
    is_last_page = False
    while is_last_page == False:

        # Find matches with the dark background in this page
        elements2 = driver.find_elements(By.CSS_SELECTOR, ".group-2.first")
        
        # Find matches with a grey background in this page
        elements1 = driver.find_elements(By.CSS_SELECTOR, ".group-1.first")

        # Add all matches to the array from top to botttom
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
        except:
            is_last_page = True
    
    for link in match_links:
        print(link)
    print(f"Found {len(match_links)} demos.")
    
    driver.quit()
    return match_links


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


def is_valid_url(url):
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc]) and "https://www.hltv.org/stats/" in url


if __name__ == '__main__':
    socketio.run(app, debug=True)
