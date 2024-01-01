import io
import os
import base64
import playwright
import playwright.sync_api
import logging
import time

from PIL import Image, ImageDraw, ImageFont

class WebEnv():
    """Web Environment providing web browsering tools."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.web_cfg = {
            'browser_args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080'
            ],
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
            'screen': {
                'width': 1920,
                'height': 1080
            },
            'timeout': 30000,
        }

        self.timeout = self.web_cfg['timeout']
        self.playwright = None
        self.browser = None
        self.page = None
        self.page_elements = [
            # {
            #     "index": element index,
            #     "selector": css selector,
            #     "xpath": xpath,
            #     "bbox": bounding box,
            #     "tagName": tag name,
            #     "text": inner text,
            # }
        ]
        self.elements_extract_js_code = open(os.path.join(
            os.path.dirname(__file__), "js", "web_elements.js")).read()

    def _check_browser(self):
        """Check if the browser is ready.
        """
        if self.page is None:
            self._setup_browser()

    def _render_page(self,) -> Image.Image:
        """Render the current page into an image.

        :return Image: The image of the current page.
        """
        screenshot = self.page.screenshot()
        return Image.open(io.BytesIO(screenshot))

    def _render_page_and_encode(self,) -> str:
        """Render the current page into an image and encode it into base64.

        :return str: The base64 encoded image of the current page.
        """
        screenshot = self.page.screenshot()
        return base64.b64encode(screenshot).decode('utf-8')

    def _render_page_with_elems_bbox(self) -> str:
        """Render the current page into an image, draw bbox for elems and encode it into base64.

        :return str: The base64 encoded image of the current page.
        """
        screenshot = self._render_page()
        if self.debug:
            timestamp = str(int(time.time()))
            screenshot_path = f"debug_figs/debug_screenshot_{timestamp}.png"
            screenshot.save(screenshot_path)
            logging.info(f"Debug screenshot saved to {screenshot_path}")
            screenshot.show()

        draw = ImageDraw.Draw(screenshot)
        elems = self._extract_elements()
        x_min, y_min = screenshot.size
        x_max, y_max = 0, 0
        font = ImageFont.truetype('arial.ttf', 18)
        for idx, elem in enumerate(elems):
            bbox = elem['bbox']
            draw.rectangle(
                [bbox['x'], bbox['y'], bbox['x'] +
                    bbox['width'], bbox['y'] + bbox['height']],
                outline="red",
                width=2
            )
            draw.text(
                [bbox['x']+bbox['width']//2, bbox['y']+bbox['height']//2],
                str(idx),
                font=font,
                fill="magenta",
            )
            x_min = min(x_min, bbox['x'])
            y_min = min(y_min, bbox['y'])
            x_max = max(x_max, bbox['x'] + bbox['width'])
            y_max = max(y_max, bbox['y'] + bbox['height'])
        screenshot_png = io.BytesIO()

        screenshot = screenshot.crop((x_min, y_min, x_max, y_max))
        if self.debug:
            timestamp = str(int(time.time()))
            screenshot_path = f"debug_figs/debug_screenshot_{timestamp}.png"
            screenshot.save(screenshot_path)
            logging.info(f"Debug screenshot saved to {screenshot_path}")
            screenshot.show()

        screenshot.save(screenshot_png, format='PNG')
        screenshot_png.seek(0)
        return base64.b64encode(screenshot_png.read()).decode('utf-8')

    def _setup_browser(self):
        """Setup or restart a browser instance.

        :return Browser: The browser instance.
        """
        if self.playwright is not None:
            self.browser.close()
            self.playwright.stop()
        self.playwright = playwright.sync_api.sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True, args=self.web_cfg['browser_args'])

        self.page = self.browser.new_page(
            user_agent=self.web_cfg['user_agent'],
            screen=self.web_cfg['screen'],
        )
        return self.browser

    def _extract_elements(self):
        """Extract elements from the current page.
        """
        elems = self.page.evaluate(self.elements_extract_js_code)
        
        for idx, elem in enumerate(elems):
            elem['index'] = idx
        self.page_elements = elems
        return elems

    def _look_page(self):
        """Look at the current page."""
        self.page.wait_for_load_state("domcontentloaded", timeout=self.timeout)
        self.page.wait_for_load_state("load", timeout=self.timeout)
        self.page.wait_for_load_state("networkidle", timeout=self.timeout)
        return {
            "type": "composite",
            "data": [
                {
                    "type": "binary",
                    "media_type": "image/png",
                    "data": self._render_page_with_elems_bbox()
                },
                {
                    "type": "simple",
                    "data": [{"index": index, "tagName": elem["tagName"], "text": elem["text"], "xpath": elem["xpath"], "bbox": elem["bbox"]} for index, elem in enumerate(self.page_elements)]
                }
            ]
        }

    def goto(self, url: str):
        """Go to the given url.

        :param string url: The url to go.
        """
        self._check_browser()
        self.page.goto(url)
        return self._look_page()

    def click(self, element_index: int = None, position: dict = None):
        """Click the target element or position on the web page.

        Click the element under the mouse cursor if neither element_index nor position is provided.

        :param integer? element_index: The index of the element to click.
        :param object? position: The position to click. Example: {"x": 0.5, "y": 0.3}, which means click the position at 50% width and 30% height. Always use relative position.
        """
        self._check_browser()
        if element_index is not None and element_index > 0 and element_index < len(self.page_elements):
            element = self.page_elements[element_index]
            bbox = element['bbox']
            self.page.mouse.click(bbox['x']+bbox['width']//2, bbox['y']+bbox['height']//2)
            print("Waiting...")
            self.page.wait_for_timeout(5000)
            print("Done.")
            return self._look_page()

        if position is not None:
            x = int(self.page.viewport_size["width"] * position['x'])
            y = int(self.page.viewport_size["height"] * position['y'])
            self.page.mouse.click(x, y)
            print("Waiting...")
            self.page.wait_for_timeout(5000)
            print("Done.")
            return self._look_page()

        self.page.mouse.down()
        self.page.mouse.up()
        print("Waiting...")
        self.page.wait_for_timeout(5000)
        print("Done.")
        return self._look_page()

    def scroll(self, x: float = 0.0, y: float = 0.6):
        """Scroll the web page.
        Example: {"x": 0.0, "y": 0.3}, which means scroll the page to 0% width and 30% height. Always use relative position.

        :param number? x: The percentage of page width to scroll. Defaults to 0.0.
        :param number? y: The percentage of page height to scroll. Defaults to 0.6.
        """
        self._check_browser()
        x = int(self.page.viewport_size["width"] * x)
        y = int(self.page.viewport_size["height"] * y)
        self.page.mouse.wheel(x, y)
        self.page.wait_for_timeout(1000)
        return self._look_page()

    def typing(self, text: str = None, press: str = 'Enter'):
        """Type the given text by triggering keyborad events.
        You can also use shortcut keys of the browser by this.

        Example:
        - Type 'Hello World' and press 'Enter': `typing(text='Hello World')`
        - Rollback to the previous page: `typing(press='Alt+ArrowLeft')`

        :param string? text: The text to type.
        :param string? press: The key to press, can be a combination of any keys. Defaults to 'Enter' . Example: 'Enter', 'Alt+ArrowLeft','Shift+KeyW'.
        """
        self._check_browser()
        self.page.keyboard.type(text)
        if press is not None:
            self.page.keyboard.press(press)
        print("Waiting...")
        self.page.wait_for_timeout(5000)
        print("Done...")
        return self._look_page()