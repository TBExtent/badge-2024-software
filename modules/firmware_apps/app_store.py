import asyncio
from typing import Any, Callable

import app
import wifi
from app_components import Menu, clear_background
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus
from urequests import get

APP_STORE_LISTING_URL = "https://apps.badge.emfcamp.org/demo_api/apps.json"

CODE_INSTALL = "CodeInstall"
AVAILABLE = "Available"
INSTALLED = "Installed"
UPDATE = "Update"
REFRESH = "Refresh Apps"


class AppStoreApp(app.App):
    state = "init"

    def __init__(self):
        super().__init__()
        self.menu = Menu(
            self,
            menu_items=[
                CODE_INSTALL,
                # AVAILABLE,
                # UPDATE,
                # INSTALLED
            ],
            select_handler=self.on_select,
            back_handler=self.on_cancel,
        )
        self.available_menu = None
        self.installed_menu = None
        self.update_menu = None
        self.codeinstall = None
        self.app_store_index = []

    def connect_wifi(self):
        ssid = wifi.get_ssid()
        if not ssid:
            print("No WIFI config!")
            return

        if not wifi.status():
            wifi.connect()
            while True:
                print("Connecting to")
                print(f"{ssid}...")
                if wifi.wait():
                    # Returning true means connected
                    break

    async def run(self, render_update):
        await render_update()

        while True:
            await asyncio.sleep(2)
            await render_update()

    def check_wifi(self):
        self.update_state("checking_wifi")
        self.connect_wifi()
        return True

        if self.state != "checking_wifi":
            self.update_state("checking_wifi")
        connected = wifi.status()
        print(wifi.get_ip())
        print("Connected" if connected else "Not connected")
        if not connected:
            self.update_state("no_wifi")
        print(wifi.get_sta_status())
        return connected

    async def get_index(self):
        if not self.check_wifi():
            return
        self.update_state("refreshing_index")
        response = get(APP_STORE_LISTING_URL)
        self.app_store_index = response.json()["items"]
        self.available_menu = Menu(
            self,
            menu_items=[app["manifest"]["app"]["name"] for app in self.app_store_index],
            select_handler=lambda _, i: self.install_app(self.app_store_index[i]),
        )
        self.update_state("main_menu")

    def install_app(self, app):
        print(f"Installing {app}")

    def update_state(self, state):
        print(f"State Transition: '{self.state}' -> '{state}'")
        self.state = state

    def handle_code_input(self, app):
        print(f"Installing {app}")
        self.update_state("main_menu")

    async def on_select(self, value, idx):
        if value == CODE_INSTALL:
            self.codeinstall = CodeInstall(
                install_handler=lambda id: self.handle_code_input(id), app=self
            )
            self.update_state("code_install_input")
        elif value == AVAILABLE:
            self.update_state("available_menu")
        elif value == INSTALLED:
            self.update_state("installed_menu")
        elif value == UPDATE:
            self.update_state("update_menu")
        elif value == REFRESH:
            await self.get_index()

    def on_cancel(self):
        self.minimise()

    def error_screen(self, ctx, message):
        ctx.gray(1).move_to(0, 0).text(message)

    async def update(self, delta):
        if self.state == "init":
            await self.get_index()

        if self.menu:
            self.menu.update(delta)
        if self.available_menu:
            self.available_menu.update(delta)
        if self.installed_menu:
            self.installed_menu.update(delta)
        if self.update_menu:
            self.update_menu.update(delta)
        return super().update(delta)

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        clear_background(ctx)
        if self.state == "main_menu" and self.menu:
            self.menu.draw(ctx)
        elif self.state == "available_menu" and self.available_menu:
            self.available_menu.draw(ctx)
        elif self.state == "installed_menu" and self.installed_menu:
            self.installed_menu.draw(ctx)
        elif self.state == "update_menu" and self.update_menu:
            self.update_menu.draw(ctx)
        elif self.state == "no_wifi":
            self.error_screen(ctx, "No Wi-Fi connection")
        elif self.state == "checking_wifi":
            self.error_screen(ctx, "Checking\nWi-Fi connection")
        elif self.state == "refreshing_index":
            self.error_screen(ctx, "Refreshing app store index")
        elif self.state == "code_install_input" and self.codeinstall:
            self.codeinstall.draw(ctx)
        else:
            self.error_screen(ctx, "Unknown error")
        ctx.restore()

        self.draw_overlays(ctx)


class CodeInstall:
    def __init__(self, install_handler: Callable[[str], Any], app: app.App):
        self.install_handler = install_handler
        self.state = "input"
        self.id: str = ""
        eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _handle_buttondown(self, event: ButtonDownEvent):
        print(event)
        if BUTTON_TYPES["UP"] in event.button:
            self.id += "0"
        elif BUTTON_TYPES["RIGHT"] in event.button:
            self.id += "1"
        elif BUTTON_TYPES["CONFIRM"] in event.button:
            print("confirm")
            self.id += "2"
        elif BUTTON_TYPES["DOWN"] in event.button:
            self.id += "3"
        elif BUTTON_TYPES["LEFT"] in event.button:
            self.id += "4"
        elif BUTTON_TYPES["CANCEL"] in event.button:
            self.id += "5"

        print(self.id)

        if len(self.id) == 8:
            eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
            self.install_handler(self.id)

    def draw(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.gray(1).move_to(0, 0).text(self.id)
        ctx.restore()
