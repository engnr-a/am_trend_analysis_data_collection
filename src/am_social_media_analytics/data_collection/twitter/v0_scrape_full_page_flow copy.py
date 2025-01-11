import time
from datetime import datetime, timedelta
import random
import csv
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from prefect import task, flow
from prefect.logging import get_run_logger
from prefect.context import FlowRunContext, TaskRunContext

from am_social_media_analytics.data_collection.common_utils.login_flow import (
    initialize_browser_with_existing_session,
    perform_login_task,
)
from am_social_media_analytics.data_collection.twitter.data_query_utils_flow import (
    create_query_string,
)
from am_social_media_analytics.data_collection.common_utils.email_service_v2 import (
    send_flow_info_by_email,
)
from am_social_media_analytics.data_collection.common_utils.general_utils import (
    calculate_scraping_time,
    set_browser_zoom,
    update_search_query_and_send_email,
    get_latest_article_with_key
)


@task
def extract_articles_from_page(url: str, search_query: str, max_hours: int):
    """
    Extracts <article> elements from a webpage, scrolling incrementally and storing
    unique content in a set. Outputs the results to a CSV file when at least 20
    elements are collected.

    Args:
        url (str): The URL of the page to scrape.
        search_query (str): The string to search twitter by
    """

    # Use prefect-native logger
    logger = get_run_logger()

    # Setup needed parameters for time-based scrapping mechanism
    start_time, end_time, hours, minutes = calculate_scraping_time(max_hours)

    # initialize the browser..NOTE: that this returns an instance of driver
    browser = initialize_browser_with_existing_session()

    # set browser to 80%
    # set_browser_zoom(browser, 80)

    # Infer data output folder and base folder..to ensure generality
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_output_folder = os.path.join(
        os.path.abspath(os.path.join(script_dir, "../../../../")),
        "data/keyphrase_search_results_raw/by_date",
    )
    logger.info(f"📂 Data output folder inferred as : {data_output_folder}")

    # Set the output csv file header
    output_csv_header = [
        "Author Name",
        "Author ID",
        "Date",
        "Post Text",
        "Replies",
        "Likes",
        "Reshares",
        "Views",
    ]

    try:
        ##########################################################################################################################
        ################## BLOCK 1: Check for authenticated session. Sign-in if there no authenticated session ##################
        ##########################################################################################################################
        if "linkedin.com" in url:
            logger.info("🔗 Detected LinkedIn. Proceeding with login...")
            perform_login_task("https://www.linkedin.com/login")
        elif "x.com" in url or "twitter.com" in url:
            logger.info("🔗 Detected Twitter (X.com). Proceeding with login...")
            perform_login_task("https://x.com/i/flow/login")
        else:
            logger.error(f"❌ Unsupported platform: {url}")
            return
        logger.info("✅ Authentication successful. Starting article extraction...")
        time.sleep(10)
        #######################################################################################################################

        ############################################################################################
        ##################  BLOCK 2: Get the given url  ###################################
        ############################################################################################
        logger.info(f"🔍 Navigating to: {url}...")
        browser.execute_script(f"window.open('{url}', '_blank');")
        # Switch to the newly opened tab
        browser.switch_to.window(browser.window_handles[-1])
        browser.get(url)
        time.sleep(10)
        ############################################################################################

        ###################################################################################################################
        ##################  BLOCK 3: Enter seatch query and then click on "latest" tab  ##################################
        ###################################################################################################################
        try:
            # Wait and find the search input field
            time.sleep(20)
            search_input = browser.find_element(
                By.CSS_SELECTOR, '[placeholder="Search"]'
            )
            search_input.click()
            logger.info("✅ Clicked on the search input field.")

            # Enter the search query
            search_input.send_keys(search_query)
            logger.info(f"✅ Entered search query: {search_query}")

            time.sleep(5)
            # Press Enter to send the search query
            search_input.send_keys(Keys.RETURN)
            logger.info("✅ Search query submitted by pressing Enter.")
        except Exception as e:
            logger.error(
                f"❌ Error interacting with the search input field: {e}", exc_info=True
            )

        time.sleep(15)
        try:
            # Find and click the "Latest" option
            latest_button = browser.find_element(By.XPATH, '//span[text()="Latest"]')
            latest_button.click()
            logger.info("✅ Clicked on the 'Latest' option.")
        except Exception as e:
            logger.error(f"❌ Error clicking on the 'Latest' option: {e}")
        time.sleep(10)
        ##############################################################################################################

        ###################
        # set_browser_zoom(browser, 25)
        ###################

        ############# [TRACKING AND CONTIUOUS VARIABLES]  ###################################################
        articles_set = set()
        scroll_count = 0
        ###
        batch_size = 500  # Write to file after every #batch items minimum
        batch_counter = 0  # Counter to track how many items have been written
        total_written = 0  # Counter for all written items
        ###

        ### I have noticied that some tweets are breakpoints: where the pages fails to load with new teets after these kind of tweets are encountered
        ### to handle this, I am keeping count of unique_keys...then skip to next day when this is encountered while sending email notification to
        ### keep track of such senarion. This is handled by the prefect task named "pdate_search_query_and_send_email"
        # Initialize a counter dictionary to track occurrences of unique keys
        unique_key_counter = {}
        # List to collect tweet keys that need updating
        problematic_tweet_keys = []
        ####################################################################################################

        ###################################################################################################################
        ##################  BLOCK 4: Set up tracking of uniquness of tweets ###############################################
        ###################################################################################################################
        # The "new_unique_keys" will store only the new unique keys to preventing.  the need to overwrite entire unique keys all the time
        
        
        new_unique_keys = (
            set()
        )  
        # The csv file containing all tweets collected so far as identified by generated unique keys
        unique_keys_file = os.path.join(script_dir, "unique_keys.csv")
        try:
            with open(unique_keys_file, "r") as f:
                all_unique_keys = set(
                    line.strip() for line in f if line.strip()
                )  # Use a set for fast lookup
            logger.info(
                f"📂 The file '{unique_keys_file}' was found. Total unique keys loaded: {len(all_unique_keys)}."
            )
        except FileNotFoundError:
            logger.error(
                f"❌ The file '{unique_keys_file}' for tracking unique tweets was not found. Stopping the workflow."
            )
            raise FileNotFoundError(
                f"The file '{unique_keys_file}' is required but was not found. Please ensure it exists in the same directory."
            )

        ##################################################################################################################
        # NOTE:####### MAIN BLOCK ###########################################################################################
        ##################################################################################################################
        stop_threshold = 500000
        while total_written < stop_threshold:
            ##--> STEP 1: Implementation of time-based run. The flow should only run for specified period of time
            current_run_time = datetime.now()
            if current_run_time >= end_time:
                logger.info(
                    "⏰ The maximum allowed scraping time has been reached. Stopping the workflow."
                )
                logger.info(
                    "📁 Writing already collected data to file due to elapsed time."
                )
                output_file = f"{data_output_folder}/tweets_final_due_to_elapsedtime_{current_run_time.strftime('%Y%m%d_%H%M%S')}.csv"

                # write out the article sets
                with open(output_file, mode="w", encoding="utf-8", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(output_csv_header)
                    writer.writerows(
                        list(articles_set)
                    )  # Write all collected articles to the file
                logger.info(f"✅ Collected data written to file: {output_file}.")

                # write out the unique keys
                if new_unique_keys:
                    with open(
                        unique_keys_file, "a", newline=""
                    ) as f:  # Open in append mode
                        writer = csv.writer(f)
                        for key in sorted(new_unique_keys):  
                            writer.writerow([key])
                logger.info(
                    f"✅ Appended {len(new_unique_keys)} new unique keys to '{unique_keys_file}'."
                )
                break
            else:
                # Log the time remaining
                remaining_time = end_time - current_run_time
                logger.info(f"⏳ Time remaining for scrapping: {remaining_time}.")

            ##--> STEP 2: Find all <article> elements that are direct children of <div class="css-175oi2r">
            articles = browser.find_elements(
                By.XPATH, '//div[contains(@class, "css-175oi2r")]/article'
            )
            
            if not articles:
                retries = 0
                max_retries = 5
                while retries < 5:
                    logger.warning(f"⚠️ No articles found. Retrying {retries + 1}/{max_retries}...")

                    # Scroll to load more articles
                    browser.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                    time.sleep(20)  # Wait for content to load

                    # Find articles again
                    articles_after_retry = browser.find_elements(By.XPATH, '//div[contains(@class, "css-175oi2r")]/article')
                    if articles_after_retry:
                        logger.info(f"✅ Articles found after retry {retries + 1}.")
                        articles = articles_after_retry 
                    retries += 1
                # If no articles found after retries, handle the situation
                if not articles:
                    logger.error("❌ No articles found after maximum retries. Updating search query and sending email.")
                    unique_key, latest_article = get_latest_article_with_key(articles_set)
                    if unique_key:
                        logger.info(f"🔑 Generated unique key for the latest article: {unique_key}")
                    else:
                        logger.warning("⚠️ No latest article available to generate a unique key.")
                    update_search_query_and_send_email(browser, unique_key)
                    

            ##--> STEP 3: Loop through all found articles
            #              - Extract necessery metadata and actual tweets
            #              - add it to the
            for article in articles:
                try:
                    ##--> STEP 3.1: Extract the author name
                    try:
                        author_name_element = article.find_element(
                            By.XPATH,
                            './/span[contains(@class, "css-1jxf684") and contains(@class, "r-bcqeeo") and contains(@class, "r-qvutc0")]',
                        )
                        author_name = (
                            author_name_element.text
                            if author_name_element
                            else "Unknown Author"
                        )
                    except Exception as e:
                        author_name = "Unknown Author"
                        print(f"❌ Error extracting tweet data (i.e. author name): {e}")

                    ##--> STEP 0: Extract the ID of the post author
                    id_element = article.find_element(
                        By.XPATH,
                        './/div[contains(@class, "css-175oi2r")]/div/div[contains(@class, "css-175oi2r")]/a/div/span',
                    )
                    post_author_id = id_element.text if id_element else None

                    ## STEP 3: Extract the date
                    date = article.find_element(By.XPATH, ".//time").get_attribute(
                        "datetime"
                    )

                    ## STEP 4: Extract the actual post text
                    try:
                        post_text_div = article.find_element(
                            By.XPATH, './/div[@data-testid="tweetText"]'
                        )
                        spans = post_text_div.find_elements(
                            By.XPATH, ".//span"
                        )  # Find all span elements
                        post_text = " ".join(
                            [span.text for span in spans if span.text.strip()]
                        )  # Concatenate text
                    except Exception as e:
                        post_text = "Unknown Post Content"
                        print(f"❌ Error extracting post text: {e}")
                        
                    # Create the unique key (concatenation of date and author name) for tracking the uniqueness of a tweet
                    tweet_unique_key = f"{date}_{post_author_id}"

                    ## STEP 5: Extract the post engagement data
                    # Initialize engagement counts
                    replies, reshares, likes, views, bookmarks = 0, 0, 0, 0, 0
                    try:
                        time.sleep(5)
                        # Find all elements with aria-label
                        engagement_elements = article.find_elements(By.XPATH, ".//div[@aria-label]")

                        # Initialize variable for engagement text
                        engagement_text = None

                        # Keywords to look for in aria-label
                        keywords = ["reply", "reposts", "likes", "bookmarks", "views"]

                        # Iterate through all found elements
                        for element in engagement_elements:
                            aria_label = element.get_attribute("aria-label")
                            if aria_label and any(keyword in aria_label.lower() for keyword in keywords):
                                engagement_text = aria_label
                                break  # Stop once we find a matching element

                        if not engagement_text:
                            #raise Exception("No matching aria-label found containing engagement keywords.")
                            logger.info(f"⚠️ No matching engagement aria-label found for tweet {tweet_unique_key}.")

                        #logger.info(f"Extracted aria-label: {engagement_text}")  

                        # Match and extract values
                        reply_match = re.search(r"(\d+)\s*replies?", engagement_text, re.IGNORECASE)
                        reshare_match = re.search(r"(\d+)\s*(reposts?|shares?)", engagement_text, re.IGNORECASE)
                        like_match = re.search(r"(\d+)\s*likes?", engagement_text, re.IGNORECASE)
                        view_match = re.search(r"(\d+)\s*views?", engagement_text, re.IGNORECASE)
                        bookmark_match = re.search(r"(\d+)\s*bookmarks?", engagement_text, re.IGNORECASE)

                        # Assign values if matches are found
                        replies = int(reply_match.group(1)) if reply_match else 0
                        reshares = int(reshare_match.group(1)) if reshare_match else 0
                        likes = int(like_match.group(1)) if like_match else 0
                        views = int(view_match.group(1)) if view_match else 0
                        bookmarks = int(bookmark_match.group(1)) if bookmark_match else 0

                        #logger.info(f"Replies: {replies}, Reshares: {reshares}, Likes: {likes}, Views: {views}, Bookmarks: {bookmarks}")  # Debugging output

                    except Exception as e:
                        logger.warning(f"❌ Error extracting engagement data: {e}")
                    # logger.info("Current tweet unique key: --> "+tweet_unique_key)

                    ## STEP 6:
                    # Pre create a row of data that corresponds to all necessary data about the post/tweet
                    article_data = (
                        author_name,
                        post_author_id,
                        date,
                        post_text,
                        replies,
                        likes,
                        reshares,
                        views,
                    )

                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract data from an article: {e}")

                # STEP 7: Check that the current post is not already added to the set...if its not add it to the set..otherwise log for debug
                if tweet_unique_key not in all_unique_keys:
                    logger.info(f"✅ Tweet with unique key:{tweet_unique_key} added to set.")
                    logger.info(
                        f"🆔 Current tweet engagements: Replies: {replies}, Reshares: {reshares}, Likes: {likes}, Views: {views}"
                    )
                    all_unique_keys.add(tweet_unique_key)  # Add to the global set
                    new_unique_keys.add(tweet_unique_key)  # Add to the new keys set
                    articles_set.add(article_data) #NOTE: most important -- add to the article set being collected
                    batch_counter += 1  # Increment batch counter
                else:
                    # Increment the counter for the duplicate key
                    if tweet_unique_key in unique_key_counter:
                        unique_key_counter[tweet_unique_key] += 1
                        occurrence_count = unique_key_counter[tweet_unique_key]
                        
                    else:
                        unique_key_counter[tweet_unique_key] = 1
                        occurrence_count = unique_key_counter[tweet_unique_key]
                        
                    logger.info(f"✋ Tweet with unique key: {tweet_unique_key} is already processed. Occurrence count: {occurrence_count}.")   
                    logger.info(f"🆔 Tweet engagements: Replies: {replies}, Reshares: {reshares}, Likes: {likes}, Views: {views}")

                    # Check if the tweet has been repeatedly tried to be processed for more than 5 times
                    if occurrence_count > 50:
                        logger.warning(
                            f"⚠️ Detected the end of the page or breaking point tweet. Tweet {tweet_unique_key} has been repeated {occurrence_count} times."
                        )
                        #update_search_query_and_send_email(browser, tweet_unique_key)
                        problematic_tweet_keys.append(tweet_unique_key)
                        
            # if problematic_tweet_keys:
            #     update_search_query_and_send_email(browser, problematic_tweet_keys[0])
            #     unique_key_counter.clear()  # Reset the counter

            ######
            #  # STEP 8: Check that we already have enough data for the batch, and writeout if we do.
            # Write out the batch if batch_counter reaches the batch_size
            if batch_counter >= batch_size:
                # Extract the months and years from the 'Date' field in articles_set
                months_years = {
                    datetime.strptime(article[2], "%Y-%m-%dT%H:%M:%S.%fZ").strftime(
                        "%m_%Y"
                    )
                    for article in articles_set
                }
                current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Determine the filename based on unique months and years
                # The output_file is in this format tweets_20241230_123928_12_2024
                # where _20241230_123928: current date time
                #   _12_2024: the month and year of the scrapped data
                if len(months_years) == 1:
                    month_year_from_article_set = list(months_years)[0]
                    output_file = f"{data_output_folder}/tweets_{current_datetime}_{month_year_from_article_set}.csv"
                else:
                    multiple_month_and_year_from_article_set = "_".join(
                        sorted(months_years)
                    )
                    output_file = f"{data_output_folder}/tweets_{current_datetime}_{multiple_month_and_year_from_article_set}.csv"

                with open(output_file, mode="w", encoding="utf-8", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(output_csv_header)
                    # writer.writerows(list(articles_set)[-batch_counter:])  # Write only the latest batch
                    writer.writerows(list(articles_set))
                logger.info(
                    f"📁 Batch of {batch_counter} articles written to {output_file}"
                )

                # Append only the new unique keys to the file
                if new_unique_keys:
                    with open(
                        unique_keys_file, "a", newline=""
                    ) as f:  # Open in append mode
                        writer = csv.writer(f)
                        for key in sorted(
                            new_unique_keys
                        ):  # Optional: Sort keys for consistency
                            writer.writerow([key])
                logger.info(
                    f"✅ Appended {len(new_unique_keys)} new unique keys to '{unique_keys_file}'."
                )

                total_written += batch_counter
                logger.info(f"Total tweets processed so far: {total_written}")

                # Cleans ups and resets operations
                batch_counter = 0  # Reset batch counter
                # NOTE: clear the article_set
                articles_set.clear()
                # clear the new_unique_keys
                new_unique_keys.clear()
                logger.info("Sleeping for 30 seconds after writing")
                
                time.sleep(30)
            #####

            ## STEP 9: Pause for a while and scroll down to reveal more posts/tweets
            # Random pause to mimic human behavior
            pause_time = random.uniform(40, 60)
            logger.info(f"⏸  Pausing for {pause_time:.2f} seconds...")
            time.sleep(pause_time)

            logger.info(
                f"🔄 Scroll {scroll_count + 1}: Extracted {len(articles_set)} unique articles."
            )
            articles = []  # Reset the articles list to ensure fresh elements
            # # Scroll down incrementally
            browser.execute_script("window.scrollBy(0, document.body.scrollHeight);")
            scroll_count += 1
        ###################################################################################################
        ###################################################################################################

    except (KeyboardInterrupt, Exception) as e:
        output_csv_header = [
            "Author Name",
            "Author ID",
            "Date",
            "Post Text",
            "Replies",
            "Likes",
            "Reshares",
            "Views",
        ]
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        if isinstance(e, KeyboardInterrupt):
            logger.warning(
                "❗ Script interrupted by user (Ctrl + C). Performing cleanup..."
            )
            output_file = f"{data_output_folder}/tweets_final_due_to_delibratecancellation_{current_run_time.strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            logger.error(f"❌ Error during article extraction: {e}", exc_info=True)
            output_file = f"{data_output_folder}/tweets_final_due_to_exception_{current_run_time.strftime('%Y%m%d_%H%M%S')}.csv"
        # Write remaining articles in the set to a file before exiting
        if len(articles_set) > 0:

            # output_file = f"{data_output_folder}/tweets_final_due_to_exception_{current_run_time.strftime('%Y%m%d_%H%M%S')}.csv"
            with open(output_file, mode="w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(output_csv_header)
                writer.writerows(list(articles_set))  # Write remaining articles
            logger.info(
                f"📁 Final remaining articles of {batch_counter} written to {output_file}."
            )

            if new_unique_keys:
                with open(
                    unique_keys_file, "a", newline=""
                ) as f:  # Open in append mode
                    writer = csv.writer(f)
                    for key in sorted(
                        new_unique_keys
                    ):  # Optional: Sort keys for consistency
                        writer.writerow([key])
            logger.info(
                f"✅ Appended {len(new_unique_keys)} new unique keys to '{unique_keys_file}'."
            )

            logger.info(f"Total tweets processed : {total_written}")
            articles_set.clear()  # Clear the set after final write
        else:
            raise


@flow
def article_extraction_flow(
    url: str, data_folder: str, days_back: int, max_run_time: int
):
    """
    Flow to extract articles from a webpage after login.
    """
    # data_folder = "data/keyphrase_search_results_raw/by_date/03_2024"
    # days_back = 10
    # in the form  "additive manufacturing" or "3d printer" or "3d printed" or "3d printing" or "3d print" until:2024-03-04 since:2024-02-23 -filter:replies
    search_query = create_query_string(data_folder, days_back)

    # Send email for flow start

    context = FlowRunContext.get()
    # Access flow name and parameters from the context
    flow_name = context.flow.name
    parameters = context.parameters.items()
    to_email_addresses = ["sholasuleiman@outlook.com"]
    # Call the email task
    send_flow_info_by_email(
        "start",  # email type
        to_email_addresses,
        flow_name,
        parameters,
        {"tweet_search_query": search_query},
    )
    extract_articles_from_page(url, search_query, max_run_time)
    # Call the email task
    send_flow_info_by_email(
        "ended",
        to_email_addresses,
        flow_name,
        parameters,
        {"tweet_search_query": search_query},
    )


if __name__ == "__main__":
    data_folder = "data/keyphrase_search_results_raw/by_date"
    days_back = 10
    website_url = "https://x.com/"
    max_run_time = 3
    article_extraction_flow(website_url, data_folder, days_back, max_run_time)
