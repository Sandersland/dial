import unittest
from unittest.mock import patch, MagicMock, call
from copy import deepcopy

from requests import Response

from pylaunch.roku import Roku
from pylaunch.roku.main import Application, DeviceUnspecifiedException
from pylaunch.ssdp import HTTPResponse
from pylaunch import roku


class TestRoku(unittest.TestCase):
    @patch("requests.get")
    def setUp(self, mock_get):
        with open("tests/xml/example.xml") as f:
            mock_get.return_value = MagicMock(spec=Response, headers={}, text=f.read())
        self.roku = Roku("https://10.1.10.165:8060")

    def test_address(self):
        self.assertEqual(self.roku.address, "http://10.1.10.165:8060")

    @patch("requests.post")
    def test_key_press(self, mock_post):
        self.roku.key_press("Up")
        mock_post.assert_called_with(f"{self.roku.address}/keypress/Up")

    @patch("requests.post")
    def test_install_app(self, mock_post):
        self.roku.install_app(1234)
        mock_post.assert_called_with(
            f"{self.roku.address}/install/1234",
            headers={"Content-Length": "0"},
            params={},
        )

    @patch("requests.post")
    def test_type_char_urlsafe(self, mock_post):
        self.roku.type_char("a")
        mock_post.assert_called_with(f"{self.roku.address}/keypress/Lit_a")

    @patch("requests.post")
    def test_type_char_not_urlsafe(self, mock_post):
        self.roku.type_char("|")
        mock_post.assert_called_with(f"{self.roku.address}/keypress/Lit_%7C")

    @patch("pylaunch.roku.Roku.key_press")
    def test_power(self, mock_method):
        self.roku.power()
        mock_method.assert_called_with(roku.POWER)

    @patch("pylaunch.roku.Roku.type_char")
    def test_type_literal(self, mock_method):
        literal_string = "aasd"
        self.roku.type_literal(literal_string)
        self.assertEqual(mock_method.call_count, 4)
        for i, value in enumerate(mock_method.call_args_list):
            self.assertEqual(value, call(literal_string[i]))

    def test_device_type(self):
        self.assertEqual(self.roku.device_type, "urn:roku-com:device:player:1-0")

    def test_friendly_name(self):
        self.assertEqual(self.roku.friendly_name, "Whcowork TV")

    def test_manufacturer(self):
        self.assertEqual(self.roku.manufacturer, "Roku")

    def test_manufacturer_url(self):
        self.assertEqual(self.roku.manufacturer_url, "http://www.roku.com/")

    def test_model_description(self):
        self.assertEqual(
            self.roku.model_description, "Roku Streaming Player Network Media"
        )

    def test_model_name(self):
        self.assertEqual(self.roku.model_name, "LC-55LBU591U")

    def test_model_number(self):
        self.assertEqual(self.roku.model_number, "7000X")

    def test_model_url(self):
        self.assertEqual(self.roku.model_url, "http://www.roku.com/")

    def test_serial_number(self):
        self.assertEqual(self.roku.serial_number, "YN00RW847759")

    def test_udn(self):
        self.assertEqual(self.roku.udn, "uuid:29780022-9c0c-10ef-808f-00f48d382d34")

    @patch("pylaunch.core.requests.get")
    def test_info(self, response):

        with open("tests/xml/device-info.xml") as f:
            response.return_value.text = f.read()

        roku_info = self.roku.info
        self.assertIsInstance(roku_info, dict)
        self.assertTrue("power_mode" in roku_info)

    @patch("pylaunch.core.requests.get")
    def test_apps(self, response):

        with open("tests/xml/apps.xml") as f:
            response.return_value.text = f.read()

        apps = self.roku.apps
        self.assertIsInstance(apps, dict)
        self.assertTrue("Netflix" in apps)
        self.assertFalse("asdasdasd" in apps)

    @patch("requests.get")
    def test_active_app(self, response):
        with open("tests/xml/active-app.xml") as f:
            response.return_value.text = f.read()
        app = self.roku.active_app
        self.assertTrue(app.name == "Roku")
        self.assertIsInstance(app, Application)

    @patch("pylaunch.ssdp.SimpleServiceDiscoveryProtocol.broadcast")
    def test_discover(self, mock_broadcast):
        message = MagicMock(
            spec=HTTPResponse, headers={"location": "http://192.168.1.1"}
        )
        mock_broadcast.return_value = [message]
        devices = Roku.discover()
        self.assertIsInstance(devices, list)
        [self.assertIsInstance(x, Roku) for x in devices]


class TestApplication(unittest.TestCase):
    @patch("requests.get")
    def setUp(self, mock_get):
        with open("tests/xml/example.xml") as f:
            mock_get.return_value = MagicMock(spec=Response, headers={}, text=f.read())
            self.roku = Roku("https://10.1.10.165:8060")

            self.app = Application(
                name="Fake Application",
                id=123,
                type="faketype",
                subtype="is not real",
                version="abc",
                roku=self.roku,
            )

    def test_app_init(self):
        self.assertEqual(self.app.name, "Fake Application")
        self.assertEqual(self.app.id, 123)
        self.assertEqual(self.app.subtype, "is not real")
        self.assertEqual(self.app.type, "faketype")
        self.assertEqual(self.app.version, "abc")
        self.assertIsInstance(self.app.roku, Roku)

    @patch("requests.get")
    def test_icon(self, mock_get):
        self.app.icon
        mock_get.assert_called_with(
            f"{self.app.roku.address}/query/icon/{self.app.id}", stream=True
        )

    def test_icon_without_device_raises_exc(self):
        app = deepcopy(self.app)
        app.roku = None
        with self.assertRaises(DeviceUnspecifiedException):
            app.icon

    @patch("requests.post")
    def test_launch(self, mock_post):
        self.app.launch()
        mock_post.assert_called_with(
            f"{self.app.roku.address}/launch/{self.app.id}",
            headers={"Content-Length": "0"},
        )

    def test_launch_without_device_raises_exc(self):
        app = deepcopy(self.app)
        app.roku = None
        with self.assertRaises(DeviceUnspecifiedException):
            app.launch()
