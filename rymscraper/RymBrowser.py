import os
import logging
import time
from pathlib import Path
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from typing import Optional

logger = logging.getLogger(__name__)

webdriver_name: Optional[str] = os.getenv('WEBDRIVER_NAME')
driver_exec_path: Optional[str] = os.getenv('DRIVER_EXEC_PATH')

if webdriver_name == 'edge':
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver import Edge as WebdriverBrowser
elif webdriver_name == 'chrome':
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver import Chrome as WebdriverBrowser
elif webdriver_name == 'safari':
    from selenium.webdriver.safari.options import Options
    from selenium.webdriver.safari.service import Service
    from selenium.webdriver import Safari as WebdriverBrowser
else:
    # Firefox as default
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver import Firefox as WebdriverBrowser


class RymBrowser(WebdriverBrowser):
    def __init__(self, headless=True):
        logger.debug("Starting Selenium Browser : headless = %s", headless)
        self.options = Options()
        if headless:
            self.options.headless = True

        if driver_exec_path:
            assert Path(driver_exec_path).exists(), 'Given executable path for webdriver does not exist.'
            self.browser_service = Service(driver_exec_path)
        else:
            self.browser_service = None

        WebdriverBrowser.__init__(self, options=self.options, service=self.browser_service)

    def restart(self):
        self.quit()
        WebdriverBrowser.__init__(self, options=self.options, service=self.browser_service)

    def get_url(self, url):
        logger.debug("get_url(browser, %s)", url)
        while True:
            self.get(str(url))
            class_to_click_on = [
                "as-oil__btn-optin",  # cookie bar
                "fc-cta-consent",  # consent popup
                # "ad-close-button",  # advertisement banner
            ]
            for i in class_to_click_on:
                if len(self.find_elements(By.CLASS_NAME, i)) > 0:
                    self.find_element(By.CLASS_NAME, i).click()
                    logger.debug(f"{i} found. Clicking on it.")

            if len(self.find_elements(By.CLASS_NAME, "disco_expand_section_link")) > 0:
                try:
                    for index, link in enumerate(
                        self.find_elements(By.CLASS_NAME, "disco_expand_section_link")
                    ):
                        self.execute_script(
                            f"document.getElementsByClassName('disco_expand_section_link')[{index}].scrollIntoView(true);"
                        )
                        link.click()
                        time.sleep(0.2)
                except Exception as e:
                    logger.debug('No "Show all" links found : %s.', e)
            # Test if IP is banned.
            if self.is_ip_banned():
                logger.error(
                    "IP banned from rym. Can't do any requests to the website. Exiting."
                )
                self.quit()
                exit()
            # Test if browser is rate-limited.
            if self.is_rate_limited():
                logger.error("Rate-limit detected. Restarting browser.")
                self.restart()
            else:
                break
        return

    def get_soup(self):
        return BeautifulSoup(self.page_source, "lxml")

    def is_ip_banned(self):
        logger.debug("soup.title : %s", self.get_soup().title)
        return self.get_soup().title.text.strip() == "IP blocked"

    def is_rate_limited(self):
        return self.get_soup().find("form", {"id": "sec_verify"})
