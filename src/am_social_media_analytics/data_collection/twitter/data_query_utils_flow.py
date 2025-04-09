import pandas as pd
import glob
from prefect import flow, task, get_run_logger
from datetime import datetime, timedelta
from am_social_media_analytics.data_collection.common_utils.email_service_v2 import (
    send_flow_info_by_email, send_search_window_summary_email
)
import os

#NOTE: Term explanation:
# The general approach is to go from top/upper/LATEST date (e.g. December 2024) to the buttom date/lower/EARLIEST date
# This approach conforms to the search approach on twitter. 
# Hence, the data collection will go downward from the top date 
# So...the earliest date for previous run is the latest date for current run  
# Hence, this module is to get the latest date for the current run                       
@task
def get_latest_date(data_folder):
    """
    Extracts the date from files in the specified folder. If no data is present, returns the first day of the month.

    Args:
        data_folder (str): Path in the format 'data/keyphrase_search_results_raw/by_date/03_2024'.

    Returns:
        str: Date in the format 'YYYY-MM-DD'.
    """
    logger = get_run_logger()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    logger.info(f"🗃️ Current script directory: {script_dir}")
    logger.info(f"🗃️ Provided data folder directory: {data_folder}")
    
    data_folder = os.path.join(
        os.path.abspath(os.path.join(script_dir, "../../../../")),  # Go back three levels
        data_folder 
    )

    try:
        csv_files = glob.glob(f"{data_folder}/**/*.csv",recursive=True)
        logger.info(f"📂 Found {len(csv_files)} CSV files in folder: {data_folder}")

        # Concatenate data from all CSV files into a single DataFrame
        df = pd.concat((pd.read_csv(file) for file in csv_files), ignore_index=True)
        logger.info(f"🗃️ Combined data from {len(csv_files)} files into a single DataFrame with {len(df)} rows.")

        # Ensure 'Date' column exists
        if 'Date' not in df.columns:
            logger.error("❌ No 'Date' column found in the CSV files. Ensure the files have a 'Date' column.")
            raise KeyError("'Date' column missing in the CSV files.")

        # Convert 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
        # Find the earliest date
        earliest_date = df['Date'].min()
        formatted_date = earliest_date.strftime("%Y-%m-%d")
        logger.info(f"✅ Earliest date found: {formatted_date}")

        #return formatted_date
        return earliest_date

    except Exception as e:
        logger.error(f"❌ An error occurred: {e}", exc_info=True)
        raise
    
    
@task
def create_query_string(data_folder, days_back):
    """
    Creates a search query string with dynamic date parameters.

    Args:
        data_folder (str): Path to the folder containing data files.
        days_back (int): Number of days to subtract from the earliest run date.

    Returns:
        str: A search query string.
    """
    logger = get_run_logger()

    # STEP 1: Get the earliest run for the month
    earliest_run = get_latest_date(data_folder)
    logger.info(f"🗓️ Earliest run date: {earliest_run}")

    # STEP 2: Convert earliest run to datetime object
    try:
        #earliest_date = datetime.strptime(earliest_run, "%Y-%m-%d")
        earliest_date = earliest_run if isinstance(earliest_run, datetime) else datetime.strptime(earliest_run, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"❌ Invalid date format for earliest run: {earliest_run}")
        logger.error(e)
        raise

    # STEP 3: Calculate the "since" date (i.e. the earliest part)
    since_date = earliest_date - timedelta(days=days_back)

    # STEP 4: Format dates for the query string
    until_date_str = earliest_date.strftime("%Y-%m-%d")
    # STEP 4.1: Modify the "until" date by adding 2 day....this is to handle lags

    # until_date_modified = earliest_date + timedelta(days=1)
    # until_date_modified = until_date_modified.strftime("%Y-%m-%d")
    #########################################################################################
    send_summary_email = False
    if earliest_date.time() >= datetime.strptime("18:00:00", "%H:%M:%S").time():
        until_date_modified = earliest_date + timedelta(days=1)
        logger.info(f"🕕Earlierst date {earliest_date} NOT within last 6 hours of the day.")
        logger.info("🌅 NOTE: Lags WON'T be considered")
        #-
    else:
        logger.info(f"🕕 Earliest datetime {earliest_date} IS within the last 6 hours of the day")
        logger.info("🌅 NOTE: Lags WILL be considered")
        until_date_modified = earliest_date
        send_summary_email = True  # Flag to send summary email
        
    until_date_modified = until_date_modified.strftime("%Y-%m-%d")
    #########################################################################################
    since_date_str = since_date.strftime("%Y-%m-%d")
    
    
    # Log both actual and modified "until" dates
    logger.info("=== 🗓️ Generated dates to be used for twitter search query ======")
    logger.info(f"🗓️ Actual 'until' date: {until_date_str}")
    logger.info(f"🗓️ Modified 'until' date: {until_date_modified}")
    logger.info(f"🗓️ Since date: {since_date_str}")


    # STEP 5: Construct the search query string
    search_query = (
        "\"additive manufacturing\" or \"3d printer\" or \"3d printed\" or \"3d printing\" "
        f"or \"3d print\" until:{until_date_modified} since:{since_date_str} -filter:replies"
    )

    logger.info(f"🔍 Generated search query: {search_query}")
    
    if send_summary_email:
        send_search_window_summary_email.submit(
            email_list=["sholasuleiman1@gmail.com"],
            node_id="node1",
            since_date=since_date_str,
            until_date=until_date_modified,
            query="(query will be shown below)"
        )
    return search_query


if __name__ == "__main__":
    data_folder = "data/keyphrase_search_results_raw/by_date/03_2024"
    days_back = 30

    result_query = create_query_string(data_folder, days_back)
    print(f"Search Query: {result_query}")
