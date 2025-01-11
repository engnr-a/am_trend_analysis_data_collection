from datetime import datetime, timedelta
import time
import csv
from prefect import flow, task, get_run_logger

from prefect import flow, task
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from am_social_media_analytics.data_collection.common_utils.login_flow import initialize_browser_with_existing_session
from am_social_media_analytics.data_collection.common_utils.email_service_v2 import send_search_query_update_email

from prefect.cache_policies import NONE

def format_engagement_data(replies, reshares, likes, views):
    return f"🆔 Tweet engagements: Replies: {replies}, Reshares: {reshares}, Likes: {likes}, Views: {views}"

@task(cache_policy=NONE)
def calculate_scraping_time(max_hours):
    """
    Validates and parses the max_hours input, and calculates the start and end times.

    Args:
        max_hours (float): The maximum duration in hours (can include fractions).

    Returns:
        tuple: A tuple containing the start time, end time, hours, and minutes.

    Raises:
        ValueError: If the input is invalid or not a positive number.
    """
    logger = get_run_logger()
    try:
        max_hours = float(max_hours)
        if max_hours <= 0:
            raise ValueError("Maximum hours must be a positive number.")
        hours = int(max_hours)
        minutes = int((max_hours - hours) * 60)  # Convert fractional part to minutes
    except ValueError as e:
        logger.error(f"❌ Invalid input for max_hours: {e}")
        raise

    start_time = datetime.now()
    end_time = start_time + timedelta(hours=hours, minutes=minutes)
    logger.info(f"🕒 Scraping started at {start_time}. Allowed time: {hours} hours and {minutes} minutes. Scheduled to end by {end_time}.")
    return start_time, end_time, hours, minutes


@task(cache_policy=NONE)
def set_browser_zoom(driver, zoom_percentage: int):
    """
    Task to set the browser zoom level using an existing driver instance.

    Args:
        driver: An active Selenium WebDriver instance.
        zoom_percentage (int): The desired zoom level as a percentage (e.g., 80 or 25).
    """
    try:
        # Convert percentage to a decimal (e.g., 80% -> 0.8, 25% -> 0.25)
        zoom_level = zoom_percentage / 100
        # Use JavaScript to set the zoom level
        driver.execute_script(f"document.body.style.zoom='{zoom_level}'")
        print(f"✅ Browser zoom set to {zoom_percentage}%")
    except Exception as e:
        print(f"❌ Error setting browser zoom to {zoom_percentage}%: {e}")


def reconstruct_search_query(tweet_key):
    """
    Constructs a dynamic search query string based on the tweet key.
    Args:
        tweet_key: Unique tweet key, e.g., '2023-12-11T23:19:17.000Z_@corkovic_igor'.
    Returns:
        A formatted search query string.
    """
    date_str = tweet_key.split('_')[0]  # Extract the date part
    tweet_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.000Z")

    until_date = (tweet_date - timedelta(days=1)).strftime("%Y-%m-%d")
    since_date = (tweet_date - timedelta(days=6)).strftime("%Y-%m-%d")

    search_query = (
        '"additive manufacturing" or "3d printer" or "3d printed" or "3d printing" '
        f'or "3d print" until:{until_date} since:{since_date} -filter:replies'
    )
    return search_query


@task(cache_policy=NONE)
def update_search_query_and_send_email(driver: webdriver, tweet_key: str):
    """
    Updates the search query dynamically based on the tweet key and sends an email notification.
    Args:
        driver: Selenium WebDriver instance.
        tweet_key: Unique key for constructing the search query.
    """
    logger = get_run_logger()
    try:
        
        logger.warning("⚠️ There has been a situation that warrants update to the search query.")
        
        logger.warning("⚠️ The search query will now be updated and notification will be sent.")
        
        # PART 1: UPDATE/RECONSTRUCT THE SEARCH QUERY
        search_query = reconstruct_search_query(tweet_key)
        logger.info(f"✍ Reconstructed search query: {search_query}")
        
        # PART 2 UPDATE THE SEARCH QUERY
        time.sleep(10)
        search_input: WebElement = driver.find_element(By.CSS_SELECTOR, '[placeholder="Search"]')
        search_input.click()
        logger.info("✅ Clicked on the search input field.")
        
        # Clear any existing text in the search input field
        search_input.send_keys(Keys.CONTROL, 'a') 
        search_input.send_keys(Keys.BACKSPACE)    
        logger.info("✅ Cleared existing text in the search input field.")
        time.sleep(15)
        
        # Enter the search query
        search_input.send_keys(search_query)
        logger.info(f"✅ Entered search query: {search_query}")

        time.sleep(10)  
        # Press Enter to submit the query
        search_input.send_keys(Keys.RETURN)
        logger.info("✅ Search query submitted by pressing Enter.")
        
        time.sleep(10)
        
        
        # PART 3 SEND EMAIL NOTIFICATION
        email_list = ["sholasuleiman@outlook.com"]
        future = send_search_query_update_email(email_list, tweet_key, search_query)
        
        
        
    except Exception as e:
        logger.error(f"❌ Error interacting with the search input field: {e}", exc_info=True)



#######################################################################################################  
@flow
def update_web_content_flow():
    """
    Prefect flow to automate the process of updating an input field using Selenium.
    """
    driver = initialize_browser_with_existing_session()

    driver.get("https://x.com")
    # css_selector = '[placeholder="Search"]'
    # search_query = "3d printing from prague"
    unique_tweet_key = "2023-10-23T14:01:49.000Z_@1shawnster"
    
    time.sleep(30)
    update_search_query_and_send_email(driver,  unique_tweet_key)
    time.sleep(30)
    


if __name__ == "__main__":
    update_web_content_flow()
    
#######################################################################################################  

def get_latest_article_with_key(articles_set):
    """
    Retrieve the latest article from the given set of articles based on the date and generate a unique key.
    Args:
        articles_set (set): Set of articles, where each article is a tuple with data including date.
    Returns:
        tuple: (unique_key, latest_article), or (None, None) if the set is empty.
    """
    from datetime import datetime

    if not articles_set:
        return None, None

    sorted_articles = sorted(
        articles_set, key=lambda x: datetime.strptime(x[2], "%Y-%m-%dT%H:%M:%S.%fZ"), reverse=True
    )
    latest_article = sorted_articles[0]  # Most recent article

    # Generate a unique key based on date and author ID
    unique_key = f"{latest_article[2]}_{latest_article[1]}"

    return unique_key, latest_article
# @flow
# def browser_zoom_flow():
#     """
#     Prefect flow to control browser zoom using an existing driver instance.
#     """
#     driver = initialize_browser_with_existing_session()
#     try:
#         # Navigate to an example page (replace with your target URL)
#         driver.get("https://www.nairaland.com")

#         set_browser_zoom(driver, 80)
        
#         time.sleep(20)

#         # Step 2: Set browser zoom to 25%
#         set_browser_zoom(driver, 25)
        
#         time.sleep(20)
#     finally:
#         driver.quit()


# # Run the flow
# if __name__ == "__main__":
#     browser_zoom_flow()
#######################################################################################################  