from am_social_media_analytics.data_collection.common_utils.login_flow import perform_login_flow


import time
from datetime import datetime
import random
import csv
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from prefect import task, flow
from prefect.logging import get_run_logger

from am_social_media_analytics.data_collection.common_utils.login_flow import initialize_browser_with_existing_session, perform_login_task, is_session_authenticated


@task
def extract_articles_from_page(url: str):
    """
    Extracts <article> elements from a webpage, scrolling incrementally and storing
    unique content in a set. Outputs the results to a CSV file when at least 20
    elements are collected.

    Args:
        url (str): The URL of the page to scrape.
    """
    logger = get_run_logger()
    browser = initialize_browser_with_existing_session()

    try:
        logger.info(f"🔍 Navigating to: {url}...")
        browser.execute_script(f"window.open('{url}', '_blank');")
        # Switch to the newly opened tab
        browser.switch_to.window(browser.window_handles[-1])
        browser.get(url)
        time.sleep(20)
        try:
            # Find and click the "Latest" option
            latest_button = browser.find_element(By.XPATH, '//span[text()="Latest"]')
            latest_button.click()
            logger.info("✅ Clicked on the 'Latest' option.")
        except Exception as e:
            logger.error(f"❌ Error clicking on the 'Latest' option: {e}")
        time.sleep(20)
        #browser.get(url)

        # Identify platform and perform login if required
        if "linkedin.com" in url:
            logger.info("🔗 Detected LinkedIn. Proceeding with login...")
            perform_login_task("https://www.linkedin.com/login")
        elif "x.com" in url or "twitter.com" in url:
            logger.info("🔗 Detected Twitter (X.com). Proceeding with login...")
            perform_login_task("https://x.com/i/flow/login")
        else:
            logger.error(f"❌ Unsupported platform: {url}")
            return

        # Check if session is authenticated
        if not is_session_authenticated(url):
            logger.error("❌ Authentication failed. Cannot proceed with extraction.")
            return

        logger.info("✅ Authentication successful. Starting article extraction...")
        time.sleep(20)
        # Scroll incrementally and extract <article> elements
        articles_set = set()
        scroll_count = 0
        
        ###
        batch_size = 500  # Write to file after every 10,000 items
        batch_counter = 0   # Counter to track how many items have been written
        total_written = 0   # Counter for all written items
        ###
        ###################################################################################################
        ###################################################################################################
        all_unique_keys = []
        while len(articles_set) < 5000000:
            # Find all <article> elements that are direct children of <div class="css-175oi2r">
            articles = browser.find_elements(By.XPATH, '//div[contains(@class, "css-175oi2r")]/article')
            for article in articles:
                try:
                    # STEP1: Extract the author name
                    try:
                        author_name_element = article.find_element(By.XPATH, './/span[contains(@class, "css-1jxf684") and contains(@class, "r-bcqeeo") and contains(@class, "r-qvutc0")]')
                        author_name = author_name_element.text if author_name_element else "Unknown Author"
                    except Exception as e:
                        author_name = "Unknown Author"
                        print(f"❌ Error extracting author name: {e}")

                    # Extract the ID of the post author
                    id_element = article.find_element(By.XPATH, './/div[contains(@class, "css-175oi2r")]/div/div[contains(@class, "css-175oi2r")]/a/div/span')
                    post_author_id = id_element.text if id_element else None


                    # Extract the date
                    date = article.find_element(By.XPATH, './/time').get_attribute('datetime')

                    # # Extract the actual post text
                    try:
                        post_text_div = article.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                        spans = post_text_div.find_elements(By.XPATH, './/span')  # Find all span elements
                        post_text = " ".join([span.text for span in spans if span.text.strip()])  # Concatenate text
                    except Exception as e:
                        post_text = "Unknown Post Content"
                        print(f"❌ Error extracting post text: {e}")
                    
                    try:
                        engagement_element = article.find_element(By.XPATH, './/div[@aria-label]')
                        engagement_text = engagement_element.get_attribute("aria-label")  # Extract the aria-label text

                        # Initialize variables
                        replies = 0
                        reshares = 0
                        likes = 0
                        views = 0

                        # Match and extract values from engagement text
                        reply_match = re.search(r'(\d+) replies?', engagement_text)
                        reshare_match = re.search(r'(\d+) reposts?', engagement_text)
                        like_match = re.search(r'(\d+) likes?', engagement_text)
                        view_match = re.search(r'(\d+) views?', engagement_text)

                        # Assign values if matches are found
                        if reply_match:
                            replies = int(reply_match.group(1))
                        if reshare_match:
                            reshares = int(reshare_match.group(1))
                        if like_match:
                            likes = int(like_match.group(1))
                        if view_match:
                            views = int(view_match.group(1))

                        print(f"Replies: {replies}, Reshares: {reshares}, Likes: {likes}, Views: {views}")
                    except Exception as e:
                        print(f"❌ Error extracting engagement data: {e}")
                    
                    # Create the unique key (concatenation of date and author name) for tracking the uniqueness of a tweet
                    tweet_unique_key = f"{date}_{post_author_id}"
                    logger.info("Current tweet unique key: --> "+tweet_unique_key)
                    # Add to the set
                    article_data = (
                        author_name,
                        post_author_id,
                        date,
                        post_text,
                        replies,
                        likes,
                        reshares,
                        views
                    )

                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract data from an article: {e}")
                #if article_data not in articles_set:
                if tweet_unique_key not in all_unique_keys:
                    all_unique_keys.append(tweet_unique_key)
                    articles_set.add(article_data)
                    batch_counter += 1  # Increment batch counter
                else:
                    logger.info("Current unique key: "+ tweet_unique_key + " is already present. Hence, not appending.")

            ######
            # Write out the batch if batch_counter reaches the batch_size
            if batch_counter >= batch_size:
                current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"articles_batch_{total_written + 1}_{current_datetime}.csv"
                with open(output_file, mode="w", encoding="utf-8", newline="") as file:
                    writer = csv.writer(file)
                    if total_written == 0:  # Add headers for the first file
                        writer.writerow([
                            "Author Name",
                            "Author ID",
                            "Date",
                            "Post Text",
                            "Replies",
                            "Likes",
                            "Reshares",
                            "Views"
                        ])
                    writer.writerows(list(articles_set)[-batch_counter:])  # Write only the latest batch

                logger.info(f"📁 Batch of {batch_counter} articles written to {output_file}")
                total_written += batch_counter
                batch_counter = 0  # Reset batch counter  
                logger.info("Sleeping for 30 seconds after writing")
                time.sleep(30)          
            #####
            # Random pause to mimic human behavior
            pause_time = random.uniform(30, 40)
            logger.info(f"⏸ Pausing for {pause_time:.2f} seconds...")
            time.sleep(pause_time)
            
            logger.info(f"🔄 Scroll {scroll_count + 1}: Extracted {len(articles_set)} unique articles.")
            # # Scroll down incrementally
            browser.execute_script("window.scrollBy(0, document.body.scrollHeight);")
            scroll_count += 1

        if batch_counter > 0:
            current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"articles_batch_{total_written + 1}_{current_datetime}.csv"
            with open(output_file, mode="w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                if total_written == 0:  # Add headers if no previous batches
                    writer.writerow([
                        "Author Name",
                        "Author ID",
                        "Date",
                        "Post Text",
                        "Replies",
                        "Likes",
                        "Reshares",
                        "Views"
                    ])
                writer.writerows(list(articles_set)[-batch_counter:])  # Write only the latest batch

            logger.info(f"📁 Final batch of {batch_counter} articles written to {output_file}")    
                
        ###################################################################################################
        ###################################################################################################

    except Exception as e:
        logger.error(f"❌ Error during article extraction: {e}")
        # Write remaining articles in the set to a file before exiting
        if len(articles_set) > 0:
            current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"articles_final_{total_written + 1}_{current_datetime}.csv"
            with open(output_file, mode="w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Author Name",
                    "Author ID",
                    "Date",
                    "Post Text",
                    "Replies",
                    "Likes",
                    "Reshares",
                    "Views"
                ])
                writer.writerows(list(articles_set))  # Write remaining articles
            logger.info(f"📁 Final remaining articles written to {output_file}.")
            articles_set.clear()  # Clear the set after final write
            raise
    # finally:
    #     #browser.quit()
    #     logger.info("🚪 Browser session closed.")


@flow
def article_extraction_flow(url: str):
    """
    Flow to extract articles from a webpage after login.
    """
    extract_articles_from_page(url)


if __name__ == "__main__":
    # Example usage
    website_url = "https://x.com/hashtag/AdditiveManufacturing?src=hashtag_click"
    article_extraction_flow(website_url)
