from bs4 import BeautifulSoup
import pandas as pd

# Assuming the corrected path to the HTML content file
file_path = "linkedin_page_2024-04-10_20-44-56.txt"  # Update this with the actual path

# Read the HTML content from the file
with open(file_path, "r", encoding="utf-8") as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, "html.parser")

companies_info = []

for item in soup.select("li.pvs-list__paged-list-item"):
    company_name = item.find("span", {"aria-hidden": "true"}).get_text(strip=True) if item.find("span", {"aria-hidden": "true"}) else "No Name"
    
    # Check if the <a> element exists and extract the URL if it does
    a_tag = item.find("a", {"data-field": "active_tab_companies_interests"})
    company_url = a_tag['href'] if a_tag and 'href' in a_tag.attrs else "No URL"
    
    followers_text = item.find("span", class_="pvs-entity__caption-wrapper").get_text(strip=True) if item.find("span", class_="pvs-entity__caption-wrapper") else "No Followers Info"
    
    companies_info.append({
        "Company Name": company_name,
        "URL": company_url,
        "Followers": followers_text
    })

df = pd.DataFrame(companies_info)


df.index = range(1, len(df) + 1)
df.reset_index(inplace=True)
df.rename(columns={'index': 'Index'}, inplace=True)


output_csv_path = "followed_companies_info.csv"  

df.to_csv(output_csv_path, index=False)

print(f"CSV file has been written to {output_csv_path}")