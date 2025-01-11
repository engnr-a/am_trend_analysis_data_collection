from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from am_social_media_analytics.utils import LinkedInScrapingSetup
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
from dotenv import load_dotenv
import os

# chrome options
chrome_options = Options()
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("start-maximized")

# web driver initialization
service = Service(ChromeDriverManager().install())
browser = webdriver.Chrome(service=service, options=chrome_options)

# Env variuble loading with dotenv
load_dotenv()

# env
username = os.getenv('LINKEDIN_USERNAME')
password = os.getenv('LINKEDIN_PASSWORD')

# Login
browser.get('https://www.linkedin.com/login')
elementID = browser.find_element(By.ID, "username")
elementID.send_keys(username)
elementID = browser.find_element(By.ID, "password")
elementID.send_keys(password)
elementID.submit()
time.sleep(15) 

#TODO: damn fucking need to make this more robust

# company_pages = {
#     "3D Adept" : "https://www.linkedin.com/company/3dadept/about/",
#     "Additive Manufacturing at Fraunhofer ILT" : "https://www.linkedin.com/company/76631286/about/",
#     "FIT Additive Manufacturing Group" : "https://www.linkedin.com/company/212180/about/",
#     "3D Systems Corporation" : "https://www.linkedin.com/company/162213/about/",
#     "KraussMaffei" : "https://www.linkedin.com/company/91732/about/",
#     "Renishaw" : "https://www.linkedin.com/company/17990/about/",
#     "TWI" : "https://www.linkedin.com/company/14139/about/",
#     "GKN Aerospace" : "https://www.linkedin.com/company/10967/about/",
#     "GKN Additive" : "https://www.linkedin.com/company/27141208/about/",
#     "GKN Powder Metallurgy":"https://www.linkedin.com/company/33182201/about/",
#     "Materialise" : "https://www.linkedin.com/company/4463/about/",
# }


list_of_company_pages = ["https://www.linkedin.com/company/3dadept/about/", 
                         "https://www.linkedin.com/company/76631286/about/",
                         "https://www.linkedin.com/company/fit-additive-manufacturing-group/about/",
                        "https://www.linkedin.com/company/3d-systems/about/",
                        "https://www.linkedin.com/company/krauss-maffei/about/",
                        "https://www.linkedin.com/company/hoganas-ab/about/",
                        "https://www.linkedin.com/company/renishaw/about/",
                        "https://www.linkedin.com/company/twi/about/",
                        "https://www.linkedin.com/company/gkn-aerospace/about/",
                        "https://www.linkedin.com/company/materialise/about/"
                         ]

company_info_list = []

for company_page in list_of_company_pages:
    browser.get(company_page)
    time.sleep(10) 

    page_source = browser.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    company_info = {
        'Overview': "Not available",
        'Website': "Not available",
        "Headquarters": "Not available",
        'Industry': "Not available",
        'Company size': "Not available",
        'Specialties': "Not available",
        'Location': "Not available"
    }

    # Extract Overview
    overview_p = soup.find('p', class_='break-words')
    if overview_p:
        company_info['Overview'] = overview_p.text.strip()

    # Iterate through all dt and dd pairs
    for dt in soup.find_all('dt', class_='mb1'):
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        category = dt.text.strip()
        value = dd.text.strip()

        # For Website, capturing the href of the a tag....
        if category == 'Website' and dd.find('a'):
            value = dd.find('a')['href']

        if category in company_info:
            company_info[category] = value

    # For Specialties, capture as list if needed
    # specialties_dd = soup.find('dt', text='Specialties').find_next_sibling('dd')
    # if specialties_dd:
    #     company_info['Specialties'] = [spec.strip() for spec in specialties_dd.text.split(',')]
    
    # For Location, extracting the primary location
    primary_location_p = soup.find('div', class_='org-location-card').find('p') if soup.find('div', class_='org-location-card') else None
    if primary_location_p:
        company_info['Location'] = primary_location_p.text.strip()

    company_info_list.append(company_info)
    time.sleep(10)

# json write
output_filename = f'company_info_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
with open(output_filename, 'w') as file:
    json.dump(company_info_list, file, indent=4)

browser.quit()
