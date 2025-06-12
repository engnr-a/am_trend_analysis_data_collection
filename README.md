# About This Repository
This repository is part of one of the two main repositories created for the thesis titled:

**“Cross-Sectoral Trend Analysis in Additive Manufacturing: Deriving Insights into Business-Relevant Topics, Use Cases, and Technology Trends Through Data Mining.”**

It contains the Python-based implementation for the **data collection** pipeline, specifically focusing on social media scraping using Selenium and other automation tools. The accompanying repository handles complementary components of the overall data mining workflow.

For questions or suggestions, please contact abubakar.suleiman@tuhh.de.


## Setting Up Selenium with Google Chrome in WSL

Opting for WSL (Debian distribution) for this project stems from a preference for Linux, along with the author's comfort and experience with this environment. This choice naturally extends to using Selenium and Chrome within WSL for web scraping. Here's a concise guide to get to setting up Selenium and Chrome on WSL.
poetry run python3 src/am_social_media_analytics/web_scrapper.py

### Prerequisites

- Windows Subsystem for Linux (WSL) installed
- Python and pip installed in your WSL environment
- Poetry installed for Python package management (see https://python-poetry.org/docs/)

### Installation & Setup

#### 1. Install Google Chrome in WSL

To automate browser actions with Selenium (if you like hard/boring/failures (lol)...try using just request instead of selenium to scrape linkedin), Google Chrome needs to be installed within the WSL environ

1. **Navigate to a temporary directory..or where you like:**

    ```bash
    cd /tmp
    ```

2. **Download the latest stable version of Chrome:**

    ```bash
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    ```

3. **Install the downloaded package:**

    ```bash
    sudo dpkg -i google-chrome-stable_current_amd64.deb
    sudo apt-get install -f
    ```

4. **Confirm the installation by checking Chrome's version:**

    ```bash
    google-chrome --version
    ```
5. **To ensure everything s fine, you can start chome and have some fun browing"**

#### 2. Python Project with Poetry

Instead of having to download the driver manually and going through the trouble of ensuring browser-driver compatibility and dependencies, this project uses poetry to manage these and other depdencies. Hence, Selenium and `webdriver-manager` has been added to the pyproject.toml file. You just need to install it with peotry command whe starting/running the project afresh. 

#### Example as Used in the Project

```python
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Chrome options initialize
chrome_options = Options()

# Setup Chrome with webdriver-manager
service = Service(ChromeDriverManager().install())
browser = webdriver.Chrome(service=service, options=chrome_options)

# Example: Open a webpage
browser.get("https://www.tuhh.de")

browser.quit()
```
#### Additional Info Source:
```
1. https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps
2. https://www.tiredsg.dev/blog/install-google-chrome-wsl/
3. https://scottspence.com/posts/use-chrome-in-ubuntu-wsl
```

#### Petry Commands
- Activate the environment
`poetry shell`
- Find the path to the environment
`poetry env info --path`
- Activate the environment (manually using the output of preceeding command)
`source /home/shola/.cache/pypoetry/virtualenvs/am-social-media-analytics-dQQDr__Q-py3.11/bin/activate`
- Add a dependency: `poetry add pyarrow`
- Check/verify dependencies...e.g. `poetry run prefect --version`
- List dependencies: `poetry show`



#### Prefect Commands
- Start the prefect server
`poetry run prefect server start`
- Start the prefect agent
`prefect worker start --pool "mypc" --work-queue "default"` where `mypc` is the name of already created local worker in this case
- Deploy a flow as deployment after creating (or not) a prefeclt.yaml manifest
`prefect deploy`
- Use prefect api to set variables
`prefect variable set twitterusername abubakar.suleiman@tuhh.de.`



#### General Useful Commands
- Start chrome in debug mode
`google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile`
`google-chrome --remote-debugging-port=9222 --user-data-dir=/home/shola/chrome-profile`
<!-- - `google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile --disable-gpu` -->

`google-chrome --remote-debugging-port=9222 --user-data-dir=/home/shola/chrome-profile --disable-gpu 2>/dev/null`