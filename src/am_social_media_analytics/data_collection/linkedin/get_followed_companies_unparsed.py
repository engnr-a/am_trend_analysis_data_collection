from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import pandas as pd
import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os


# Initialize Chrome options
chrome_options = Options()
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("start-maximized")

# Initialize the WebDriver
service = Service(ChromeDriverManager().install())
browser = webdriver.Chrome(service=service, options=chrome_options)

# Credentials
load_dotenv()
username = os.getenv('LINKEDIN_USERNAME')
password = os.getenv('LINKEDIN_PASSWORD')

# Login
browser.get('https://www.linkedin.com/login')
elementID = browser.find_element(By.ID, "username")
elementID.send_keys(username)
elementID = browser.find_element(By.ID, "password")
elementID.send_keys(password)
elementID.submit()
time.sleep(60) # incase of entering code from email

# Navigate to the LinkedIn interests page
profile_page = 'https://www.linkedin.com/in/sshola/details/interests/'
browser.get(profile_page)
time.sleep(20)

# Scroll to the last section of the page
browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(60)

# Save entire text to file for later parsing by beautiful soup
page_source = browser.page_source
current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
filename = f"linkedin_page_{current_time}.txt"
with open(filename, "w", encoding="utf-8") as file:
    file.write(page_source)

