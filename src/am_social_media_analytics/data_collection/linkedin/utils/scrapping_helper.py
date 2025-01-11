from datetime import datetime
from dateutil.relativedelta import relativedelta


def convert_relative_date(relative_date_str: str) -> str:
    """
    Converts a relative date string into an actual date string.
    
    Parameters:
    - relative_date_str (str): The relative date string (e.g., "1d", "2w", "3m", "4y").
    
    Returns:
    - str: The actual date in "YYYY-MM-DD" format.
    """
    today = datetime.today()
    number_part = int(''.join(filter(str.isdigit, relative_date_str)))
    unit_part = ''.join(filter(str.isalpha, relative_date_str)).lower()  # Make case-insensitive
    
    if unit_part in ['d', 'day']:
        actual_date = today - relativedelta(days=number_part)
    elif unit_part in ['w', 'week']:
        actual_date = today - relativedelta(weeks=number_part)
    elif unit_part in ['m', 'mo', 'month']:  # Added 'mo' as an alternative for month
        actual_date = today - relativedelta(months=number_part)
    elif unit_part in ['y', 'yr', 'year']:  # Added 'yr' as an alternative for year
        actual_date = today - relativedelta(years=number_part)
    else:
        print(f"Error: Unknown time unit '{unit_part}' in relative date string '{relative_date_str}'.")  # Debugging aid
        raise ValueError("Unknown time unit in relative date string.")
    
    return actual_date.strftime('%Y-%m-%d')


def convert_abbreviated_to_number(s):
    if 'K' in s:
        return int(float(s.replace('K', '')) * 1000)
    elif 'M' in s:
        return int(float(s.replace('M', '')) * 1000000)
    else:
        return int(s)
        
        
def get_text(container, selector, attributes):
    try:
        element = container.find(selector, attributes)
        if element:
            return element.text.strip()
    except Exception as e:
        print(e)
    return ""

# Function to extract media information
def get_media_info(container):
    media_info = [("div", {"class": "update-components-video"}, "Video"),
                  ("div", {"class": "update-components-linkedin-video"}, "Video"),
                  ("div", {"class": "update-components-image"}, "Image"),
                  ("article", {"class": "update-components-article"}, "Article"),
                  ("div", {"class": "feed-shared-external-video__meta"}, "Youtube Video"),
                  ("div", {"class": "feed-shared-mini-update-v2 feed-shared-update-v2__update-content-wrapper artdeco-card"}, "Shared Post"),
                  ("div", {"class": "feed-shared-poll ember-view"}, "Other: Poll, Shared Post, etc")]
    
    for selector, attrs, media_type in media_info:
        element = container.find(selector, attrs)
        if element:
            link = element.find('a', href=True)
            return link['href'] if link else "None", media_type
    return "None", "Unknown"