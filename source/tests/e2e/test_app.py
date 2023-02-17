# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


@pytest.fixture
def browser():
    chrome_options = Options()
    # Make sure the window is large enough in headless mode so that all
    # the elements on the page are visible
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")

    browser = webdriver.Chrome(
        ChromeDriverManager().install(), chrome_options=chrome_options
    )
    return browser


def test_everything(browser, test_environment, stack_resources):
    browser.implicitly_wait(5)
    browser.get(
        test_environment.get("LOCALHOST_URL")
        or stack_resources["UserInterface"]
    )
    wait = WebDriverWait(browser, 30)
    # Login
    username_field = browser.find_element(
        "xpath", "/html/body/div/div/div/div/div[2]/div[1]/div/input"
    )
    username_field.send_keys(test_environment["EMAIL"])
    password_field = browser.find_element(
        "xpath", "/html/body/div/div/div/div/div[2]/div[2]/input"
    )
    password_field.send_keys(test_environment["PASSWORD"])
    browser.find_element(
        "xpath", "/html/body/div/div/div/div/div[3]/span[1]/button"
    ).click()
    # Validate navbar brand
    xpath = "/html/body/div/div/div/div[1]/nav/a"
    wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    navbar_brand = browser.find_elements("xpath", xpath)[0].get_attribute(
        "innerText"
    )
    assert navbar_brand == "Amazon Marketing Cloud uploader from AWS"

    # open Step 1
    browser.find_element(By.ID, "step1").click()
    # validate the value shown for s3 bucket
    element_id = "bucket-input"
    wait.until(EC.presence_of_element_located((By.ID, element_id)))
    bucket_value = browser.find_element(By.ID, element_id).get_attribute(
        "placeholder"
    )
    assert bucket_value == test_environment["DATA_BUCKET_NAME"]
    # validate the s3 bucket table
    xpath = "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div/table/tbody/tr[1]/td[2]"
    wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    xpath = (
        "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div/table/tbody/tr"
    )
    rows = browser.find_elements("xpath", xpath)
    assert len(rows) > 0

    # validate key selection when clicking top table row
    browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div/table/tbody/tr[1]/td[1]",
    ).click()

    key_input_field = browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div/div[1]/div[2]/div/input",
    )
    key_input_text = key_input_field.get_attribute("value")

    key_table_field1 = browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div/table/tbody/tr[1]/td[2]",
    )
    key_table_text1 = key_table_field1.text
    assert key_input_text == key_table_text1

    # validate multiple key selection, click second row
    browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div/table/tbody/tr[2]/td[1]",
    ).click()

    multiple_key_text = key_input_field.get_attribute("value")

    key_table_field2 = browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[2]/div/table/tbody/tr[2]/td[2]",
    )
    key_table_text2 = key_table_field2.text

    keys = key_table_text1 + ", " + key_table_text2
    assert multiple_key_text == keys

    # open Step 2
    browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div/div[2]/button",
    ).click()

    # validate if keys stored, s3 key field matches in step 2 from step 1
    s3_key_field = browser.find_element(
        "xpath",
        "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div[2]/div/input",
    )
    s3_key_text = s3_key_field.get_attribute("value")

    assert s3_key_text == keys

    # validate add to existing dataset button triggers select data dropdown
    browser.find_element("xpath", "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div[3]/div[2]/label/span").click()
    assert browser.find_element("xpath", "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div[4]/select")

    # validate create dataset button triggers name form field
    browser.find_element("xpath", "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div[3]/div[1]/label/span").click()
    assert browser.find_element("xpath", "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div[4]/div[1]/div/input")

    # open Step 2
    browser.find_element(By.ID, "step2").click()
    # Time period options should not be visible until we click FACT
    assert not len(browser.find_elements(By.ID, "time_period_options"))
    # select FACT dataset type
    browser.find_element("xpath", "/html/body/div/div/div/div[2]/div/div[2]/div[1]/div[4]/div[3]/div[1]/fieldset/div/div/div[1]/label/span").click()
    # Time period options should now be visible
    # and the first option should be selected by default
    assert len(browser.find_elements(By.ID, "time_period_options"))
    assert browser.find_element(
        By.XPATH, '//*[@id="time_period_options_BV_option_0"]'
    ).is_selected()
    # Country dropdown should be visible
    assert browser.find_element(
        By.XPATH, '//*[@id="time_period_options_BV_option_0"]'
    ).is_selected()
    # select US as country and check that the value updates
    cc_dropdown = browser.find_element(By.ID, "country-code-dropdown")
    Select(cc_dropdown).select_by_value("US")
    assert cc_dropdown.get_attribute("value") == "US"

    # Sign out
    browser.find_element(
        "xpath", "/html/body/div/div/div/div[1]/nav/div/ul/li/a"
    ).click()
