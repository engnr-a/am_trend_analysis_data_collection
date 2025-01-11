# # linkedin_scraping_setup.py
# import logging
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager
# import time
# import os
# from dotenv import load_dotenv

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# class LinkedInScrapingSetup:
#     """
#     Sets up a Chrome WebDriver for scraping LinkedIn, with optional login functionality.
#     This class manages browser options and session, and provides an option to log into LinkedIn.
#     """
#     def __init__(self):
#         logger.info("Initializing LinkedInScrapingSetup...")
#         self.browser = self.initialize_browser()

#     def initialize_browser(self):
#         """Initializes and returns a Chrome WebDriver with predefined options."""
#         logger.info("Initializing Chrome WebDriver with predefined options...")
#         chrome_options = Options()
#         chrome_options.add_argument("user-agent=Mozilla/5.0 ... Firefox/104.0")
#         chrome_options.add_argument("--no-sandbox")
#         chrome_options.add_argument("--disable-dev-shm-usage")
#         chrome_options.add_argument("start-maximized")

#         service = Service(ChromeDriverManager().install())
#         browser = webdriver.Chrome(service=service, options=chrome_options)
#         logger.info("Chrome WebDriver initialized successfully.")
#         return browser

#     def login_to_linkedin(self):
#         """Logs into LinkedIn using credentials from environment variables."""
#         logger.info("Loading environment variables...")
#         load_dotenv()  # Load environment variables from .env file
        
#         username = os.getenv('LINKEDIN_USERNAME')
#         password = os.getenv('LINKEDIN_PASSWORD')

#         logger.info("Attempting to log into LinkedIn...")
#         self.browser.get('https://www.linkedin.com/login')
#         time.sleep(15)
#         username_field = self.browser.find_element(By.ID, "username")
#         username_field.send_keys(username)
#         password_field = self.browser.find_element(By.ID, "password")
#         password_field.send_keys(password)
#         password_field.submit()
#         time.sleep(15) 
#         logger.info("Logged into LinkedIn successfully.")

#     def quit(self):
#         """Quits the browser session."""
#         logger.info("Quitting the browser session...")
#         self.browser.quit()
#         logger.info("Browser session quit successfully.")




import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInScrapingSetup:
    def __init__(self):
        logger.info("Initializing LinkedInScrapingSetup...")
        self.browser = self.initialize_browser()

    def initialize_browser(self):
        logger.info("Initializing Chrome WebDriver with predefined options...")
        chrome_options = Options()
        chrome_options.add_argument("user-agent=Mozilla/5.0 ... Firefox/104.0")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("start-maximized")

        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome WebDriver initialized successfully.")
        return browser

    def login_to_linkedin(self):
        logger.info("Loading environment variables...")
        load_dotenv()
        
        username = os.getenv('LINKEDIN_USERNAME')
        password = os.getenv('LINKEDIN_PASSWORD')

        logger.info("Attempting to log into LinkedIn...")
        self.browser.get('https://www.linkedin.com/login')

        # Wait for the username field to be present
        WebDriverWait(self.browser, 20).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        username_field = self.browser.find_element(By.ID, "username")
        password_field = self.browser.find_element(By.ID, "password")

        username_field.send_keys(username)
        password_field.send_keys(password)
        password_field.submit()

        # Additional wait to ensure login completes
        time.sleep(15)
        logger.info("Logged into LinkedIn successfully.")

    def quit(self):
        logger.info("Quitting the browser session...")
        self.browser.quit()
        logger.info("Browser session quit successfully.")
