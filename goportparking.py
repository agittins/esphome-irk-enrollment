import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import hassapi as hass
import adbase as ad

class GoPortParkingController(hass.Hass):
    def initialize(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome('chromedriver', options=chrome_options)
        self.log(f"initialized parking driver")
        self.buttons = []
        for plate in self.args['plates']:
            entity_id = f"button.quick_buy_daily_{plate}"
            self.buttons.append(entity_id)
            entity = self.get_entity(entity_id)
            entity.set_state(state='unknown', attributes={'friendly_name': f"Quick buy daily goportparking pass for {plate}", 'plate': plate})
        def filter_quick_buy_button(x):
            entity = x.get('entity_id')
            if isinstance(entity, list) and len(entity) == 1:
                entity = entity[0]
            if isinstance(entity, str):
                return entity.startswith('button.quick_buy_daily_')
            return False
        self.listen_event(self.book_daily, "call_service", domain="button", service="press", service_data=filter_quick_buy_button)

    def terminate(self):
        self.driver.close()

    def book_daily(self, event_name, data, kwargs):
        entity = data['service_data']['entity_id']
        if isinstance(entity, list) and len(entity) == 1:
            entity = entity[0]
        if not isinstance(entity, str) or not entity.startswith('button.quick_buy_daily_'):
            self.log(f"entity wasn't expected: {entity}")
            return
        button_attrs = self.get_state(entity, attribute="all")
        self.log(f"attrs of {entity} = {button_attrs}")
        plate = button_attrs['attributes']['plate']
        self.log(f"buying daily: navigating to login")
        self.driver.get("https://goportparking.org/rppportal/login.xhtml")
        time.sleep(5)
        self.log(f"buying daily: logging in")
        username = self.driver.find_element(By.ID, "username")
        username.clear()
        username.send_keys(self.args['username'])
        password = self.driver.find_element(By.ID, "password")
        password.clear()
        password.send_keys(self.args['password'])
        self.driver.find_element(By.ID, "login").click()
        time.sleep(5)
        if self.driver.current_url != 'https://goportparking.org/rppportal/index.xhtml':
            self.log(f"Login seems to have failed")
            self.get_entity(entity).set_state(state='unavailable')
            return
        self.log(f"buying daily: activating quick-buy (on url {self.driver.current_url})")
        quick_buy = self.driver.find_element(By.PARTIAL_LINK_TEXT, plate)
        quick_buy.click()
        time.sleep(5)
        self.log(f"buying daily: confirming quick-buy")
        quick_buy_confirm = self.driver.find_element(By.XPATH, "//span[@id='quickBuyConfirmPanel']//input[@Value='Yes']")
        quick_buy_confirm.click()
        print(f"bought the daily pass (confirm={quick_buy_confirm})")