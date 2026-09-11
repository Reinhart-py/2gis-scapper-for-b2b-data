import logging
from typing import TypeAlias

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

NoSuchElement: TypeAlias = NoSuchElementException

XPATHS = {
    "result_count": "(//span[@class='_1xhlznaa'])[1]",
    "scroll_container_primary": "(//div[@class='_15gu4wr'])[3]",
    "scroll_container_fallback": "(//div[@class='_15gu4wr'])[2]",
    "next_page_btn": "//div[@class='_5ocwns']//div[2]",
}


def get_default_chrome_options() -> Options:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    # Reduce disk and memory caching overhead
    options.add_argument("--disk-cache-size=104857600")  # 100MB max cache
    options.add_argument("--media-cache-size=104857600")
    # Mute media audio to conserve pipeline memory
    options.add_argument("--mute-audio")
    return options


def create_session(
    options: Options = None,
    service: Service = None,
) -> WebDriver:
    if options is None:
        options = get_default_chrome_options()
    if service is None:
        service = webdriver.ChromeService()
    driver = webdriver.Chrome(options=options, service=service)
    driver.set_page_load_timeout(45)
    driver.maximize_window()
    return driver


def quit_session(driver: WebDriver | None) -> None:
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass


def navigate(url: str, driver: WebDriver) -> None:
    driver.get(url)


def find(driver: WebDriver, xpath: str) -> WebElement:
    return driver.find_element(By.XPATH, xpath)


def scroll_into_view(driver: WebDriver, el: WebElement | None) -> None:
    if el:
        driver.execute_script("arguments[0].scrollIntoView(false);", el)


def wait(time: float, driver: WebDriver) -> None:
    driver.implicitly_wait(time)


def click_element(element: WebElement) -> None:
    element.click()
