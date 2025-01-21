from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def setup_chrome_driver():
    """Install and setup Chrome WebDriver"""
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.quit()

if __name__ == "__main__":
    print("Setting up Chrome WebDriver...")
    setup_chrome_driver()
    print("Chrome WebDriver setup complete!")
