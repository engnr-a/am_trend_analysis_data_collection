from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup as bs
import time
import json
from datetime import datetime
from am_social_media_analytics.utils import scrapping_helper as helper
import pandas as pd
from dotenv import load_dotenv
import os

chrome_options = Options()
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("start-maximized")

service = Service(ChromeDriverManager().install())
browser = webdriver.Chrome(service=service, options=chrome_options)

#####################################################################################
# Company Page
page = 'https://www.linkedin.com/company/3dadept/'

# Some preps for the output file
if page[-1] == "/":
    company_name = page.split("/")[-2]
else:
    company_name = page.split("/")[-1]

company_name = company_name.replace('-', ' ').title()
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"{company_name}_{current_time}.json"
#####################################################################################


##########################################################################################################################################################################
load_dotenv()

# Access environment variables for credentials
username = os.getenv('LINKEDIN_USERNAME')
password = os.getenv('LINKEDIN_PASSWORD')

#Open login page
browser.get('https://www.linkedin.com/login')
#Enter login info:
elementID = browser.find_element(By.ID, "username")
elementID.send_keys(username)
elementID = browser.find_element(By.ID, "password")
elementID.send_keys(password)
elementID.submit()
time.sleep(60)
##########################################################################################################################################################################


##########################################################################################################################################################################
post_page = "https://www.linkedin.com/company/3dadept/posts"
browser.get(post_page)
##########################################################################################################################################################################



##########################################################################################################################################################################
SCROLL_PAUSE_TIME = 1.5
MAX_SCROLLS = False

# JavaScript commands
SCROLL_COMMAND = "window.scrollTo(0, document.body.scrollHeight);"
GET_SCROLL_HEIGHT_COMMAND = "return document.body.scrollHeight"

# Initial scroll height
last_height = browser.execute_script(GET_SCROLL_HEIGHT_COMMAND)
scrolls = 0
no_change_count = 0

while True:
    # Scroll down to bottom
    browser.execute_script(SCROLL_COMMAND)

    # Wait to load page
    time.sleep(SCROLL_PAUSE_TIME)

    # Calculate new scroll height and compare with last scroll height
    new_height = browser.execute_script(GET_SCROLL_HEIGHT_COMMAND)
    
    # Increment no change count or reset it
    no_change_count = no_change_count + 1 if new_height == last_height else 0
    
    # Break loop if the scroll height has not changed for 3 cycles or reached the maximum scrolls
    if no_change_count >= 3 or (MAX_SCROLLS and scrolls >= MAX_SCROLLS):
        break
    
    last_height = new_height
    scrolls += 1
##########################################################################################################################################################################



##########################################################################################################################################################################

company_page = browser.page_source
linkedin_soup = bs(company_page.encode("utf-8"), "html.parser")
#print(linkedin_soup.prettify())

containers = linkedin_soup.find_all("div",{"class":"feed-shared-update-v2"})
containers = [container for container in containers if 'activity' in container.get('data-urn', '')]
print(len(containers))

#Saving the container html for bebugging purposes
containers_text = "\n\n".join([c.prettify() for c in containers])
with open(f"{company_name}_{current_time}.txt", "w+") as t:
    t.write(containers_text)


posts_data = []

# Main loop to process each container
for container in containers:
    post_text = helper.get_text(container, "div", {"class": "feed-shared-update-v2__description-wrapper"})
    media_link, media_type = helper.get_media_info(container)
    ###############################[DATE]#####################################################################################
    date_span = container.find('span', class_="update-components-actor__sub-description")
    if date_span:
        # Extracting the text directly and processing to get the date part
        post_date_text = date_span.text.strip().split('•')[0].strip()  # Extracts the date part like "1mo"
        actual_date = helper.convert_relative_date(post_date_text)
    else:
        post_date = None
    ####################################################################################################################
    
    # Reactions (likes)
    reactions_element = container.find('span', class_="social-details-social-counts__reactions-count")
    post_reactions = reactions_element.text.strip() if reactions_element else 0

    # Comments
    comment_button = container.find('button', class_="social-details-social-counts__count-value")
    if comment_button and ("comment" in comment_button.get('aria-label', '')):
        comment_text = comment_button.get('aria-label')
        # Extracting the numeric part from the text
        post_comments_str = ''.join(filter(str.isdigit, comment_text))
        print("************************")
        print(post_comments_str)
        print("************************")
        
        # Convert the string to an integer
        post_comments = int(post_comments_str) if post_comments_str.isdigit() else 0
    else:
        post_comments = 0


    # Shares
    shares_element = container.find_all(lambda tag: tag.name == 'button' and 'aria-label' in tag.attrs and 'repost' in tag['aria-label'].lower())
    shares_idx = 1 if len(shares_element) > 1 else 0
    post_shares = shares_element[shares_idx].text.strip() if shares_element and shares_element[shares_idx].text.strip() != '' else 0
        
        
    # Append the collected data to the posts_data list
    posts_data.append({
        "Page": company_name,
        "Date": actual_date,
        "Post Text": post_text,
        "Media Type": media_type,
        "Likes": post_reactions,
        "Comments": post_comments,
        "Shares":post_shares,
        #"Likes Numeric": helper.convert_abbreviated_to_number(post_reactions),
        "Media Link": media_link
    })


try:
    df = pd.DataFrame(posts_data)
except:
    for item in list(data.keys()):
        print(item)
        print(len(data[item]))
        
for col in df.columns:
    try:
        df[col] = df[col].astype(int)
    except:
        pass


# Export the DataFrame to a CSV file
csv_file = f"{company_name}_{current_time}posts.csv"
df.to_csv(csv_file, encoding='utf-8', index=False)
print(f"Data exported to {csv_file}")
##########################################################################################################################################################################
