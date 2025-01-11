######
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
from dotenv import load_dotenv
import os
from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.variables import Variable
from prefect.logging import get_run_logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# chrome options
# chrome_options = Options()
# chrome_options.add_argument("user-agent=Mozi
# lla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0")
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("start-maximized")

# web driver initialization
# service = Service(ChromeDriverManager().install())
# browser = webdriver.Chrome(service=service, options=chrome_options)

from selenium.webdriver.chrome.webdriver import WebDriver   

def initialize_browser_with_existing_session() -> WebDriver:
    """
    Initializes a WebDriver instance that connects to an existing Chrome session.
    """
    chrome_options = Options()
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222") 
    chrome_options.add_argument("--remote-debugging-port=9222")
    
     # Add settings to disable video rendering
    # chrome_prefs = {
    #     "profile.managed_default_content_settings.media_stream": 2,  # Block media streams
    #     "profile.managed_default_content_settings.images": 2,        # Optionally block images to speed up
    #     "profile.default_content_setting_values.plugins": 2,         # Disable plugins like Flash
    # }
    # chrome_options.add_experimental_option("prefs", chrome_prefs)
    
    print(ChromeDriverManager().install())
    # Initialize WebDriver using the existing session
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


@task
def is_session_authenticated(url: str) -> bool:
    """
    Checks if there's already an open browser tab where the user is authenticated 
    for the given platform.

    Parameters:
        url (str): The base URL of the platform (e.g., "https://www.linkedin.com" or "https://x.com").

    Returns:
        bool: True if an authenticated session is already available, False otherwise.
    """
    try:
        logger = get_run_logger()
        logger.info(f"🔍 Checking for existing authenticated session on: {url}...") 
        try:
            # Connect to the existing browser session
            browser = initialize_browser_with_existing_session()
            
            # Get all open tabs/windows
            open_tabs = browser.window_handles
            logger.info(f"✅ Connected to browser session. Total opened tabs: {len(open_tabs)}")
    
            if not open_tabs:
                logger.warning("⚠️ No tabs detected in the browser session.")
                return False
           
        except Exception as e:
            logger.error(f"❌ Error connecting to existsing browser session {str(e)}")
            return False
        
        
        for tab in open_tabs:
            browser.switch_to.window(tab)
            logger.info(f"🔍 Checking tab with current URL: {browser.current_url}")
            
            if browser.current_url:
                # Perform login state validation for LinkedIn
                if "linkedin.com" in url:
                    logger.info("🔍 Checking for LinkedIn related authenticated session")
                    # Check if the word "feed" is visible in the current page title or URL
                    if "feed" in browser.title.lower() or "feed" in browser.current_url.lower():
                        logger.info("✅ LinkedIn related authenticated session found")
                        return True
                    
                # Perform login state validation for X.com (Twitter)
                elif "x.com" in url:
                    logger.info("🔍 Checking for Twitter related authenticated session")
                    # First, check if "Home" is present in the title or URL
                    if "home" in browser.title.lower() or "home" in browser.current_url.lower():
                        logger.info("✅ Twitter related authenticated session found")
                        return True

                    # Second, check the page content for the word "Home"
                    try:
                        home_text = browser.find_elements(By.XPATH, '//span[text()="Home"]')
                        if len(home_text) > 0:
                            logger.info("✅ Twitter related authenticated session found")
                            return True
                    except Exception as e:
                        logger = get_run_logger()
                        logger.warning(f"Could not find 'Home' text: {str(e)}")
            else:
                logger.debug(f"⚠️ The current tab with URL '{browser.current_url}' is neither LinkedIn nor Twitter.")


        # No authenticated session found in any tab
        return False
    except Exception as e:
        logger = get_run_logger()
        logger.error(f"Error checking for an authenticated session: {str(e)}")
        return False



@task
def perform_login_task(url: str):
    """
    Opens the specified website and simulates a login if required.
    """
    try:
        logger = get_run_logger()

        if is_session_authenticated(url):
            logger.info(f"✅ Found an authenticated session for {url}. Skipping login.")
            return
        
        logger.info(f"⚠️ No authenticated session found. Opening website: {url}...") 
        browser = initialize_browser_with_existing_session()
        
        # Open a new tab
        browser.execute_script("window.open('');")
        browser.switch_to.window(browser.window_handles[-1])
        # Navigate to the specified URL
        browser.get(url)
        
        time.sleep(10)  # Allow time for potential redirection

        # Check if redirected to a URL indicating an authenticated session
        if "linkedin.com" in url and "feed" in browser.current_url:
            logger.info(f"✅ Redirected to '{browser.current_url}'. Authentication already active. Skipping login.")
            return

        # Simulate login if the website is LinkedIn
        if "linkedin.com" in url:
            logger.info("🔗 LinkedIn detected. Proceeding with LinkedIn login...")
            
            # Fetching credentials with try-except block
            try:
                logger.info("🔑 Fetching credentials...")
                linkedinusername = Variable.get('linkedinusername')
                linkedinpassword = Secret.load("linkedinpassword").get()
                logger.info("🔑 Credentials fetched successfully!")
                logger.info(f"📝 Username: {linkedinusername}")  
                logger.info("🔒 Password: [HIDDEN for obvious reason 😂]") 
            except Exception as e:
                logger.error(f"❌ Error fetching credentials: {str(e)}")
                return  # Return early if credentials fetching fails
            
            elementID = browser.find_element(By.ID, "username")
            elementID.send_keys(linkedinusername)
            logger.info("📝 Username entered!")
            elementID = browser.find_element(By.ID, "password")
            elementID.send_keys(linkedinpassword)
            logger.info("🔒 Password entered!")
            
            elementID.submit()
            logger.info("✅ LinkedIn login submitted successfully!") 
            time.sleep(180)
        # Simulate login for x.com
        elif "x.com" in url: #https://x.com/i/flow/login
            logger.info("🔗 x.com detected. Proceeding with x.com login...")
            # Wait for 30 seconds before interacting with elements
            time.sleep(30)
            
            # Fetching credentials with try-except block
            try:
                logger.info("🔑 Fetching credentials...")
                twitterusername = Variable.get('twitterusername')
                twitterpassword = Secret.load("twitterpassword").get()
                logger.info("🔑 Credentials fetched successfully!")
                logger.info(f"📝 Username: {twitterusername}")  
                logger.info("🔒 Password: [HIDDEN for obvious reason 😂]") 
            except Exception as e:
                logger.error(f"❌ Error fetching credentials: {str(e)}")
                return  

            time.sleep(45)

            # Enter the username
            username_field = browser.find_element(By.XPATH, '//input[@name="text"]')
            username_field.send_keys(twitterusername)
            logger.info("📝 Username entered!")
            time.sleep(20)

            # Click on Next
            try:
                # Wait for the button with text "Next" to be visible and clickable
                logger.info("🔍 Waiting for the 'Next' button to become clickable...")
                next_button = WebDriverWait(browser, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Next")]'))
                )
                
                logger.info("🔘 'Next' button found. Attempting to click...")
                next_button.click()
                logger.info("✅ Successfully clicked the 'Next' button.")
            except Exception as e:
                logger.error(f"❌ Error clicking the 'Next' button: {str(e)}")

            # Wait for the password field
            time.sleep(30)

            # Enter password
            password_field = browser.find_element(By.XPATH, '//input[@name="password"]')
            password_field.send_keys(twitterpassword)
            logger.info("🔒 Password entered!")

            # Click on Log In
            login_button = browser.find_element(By.XPATH, '//span[text()="Log in"]')
            login_button.click()
            logger.info("✅ Log in button clicked!")
            time.sleep(45)
    finally:
        # Ensure the browser is closed after execution
        #browser.quit()
        logger.info("✅ Entire logging flow has now completed successfully !")

@flow
def perform_login_flow(website: str):
    """
    Selenium flow to open a specified website and perform login
    """
    perform_login_task(website)

if __name__ == "__main__":
    #perform_login_flow(website="https://www.linkedin.com/login") 
    perform_login_flow(website="https://x.com/i/flow/login") 
