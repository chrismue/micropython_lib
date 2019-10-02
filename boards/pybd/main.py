import pyb
import _thread
import time

import network
from microWebSrv import MicroWebSrv

from led36 import led36
from lsm9ds1 import LSM9DS1


class LedTile:
    def __init__(self):
        self._tile = led36()
        self._tile.brightness(100)
        self._tile.illu(0, 0, 0)

    def set_color(self, r, g, b):
        self._tile.illu(r, g, b)


class ThreadedMeasuring:
    def __init__(self, led_tile):
        # Initialize internal variables
        self._r = 0
        self._g = 0
        self._led_tile = led_tile

        # Initialize Inertial Module
        i2c_y = pyb.I2C(2, pyb.I2C.MASTER, baudrate=100000)
        self._lsm9d1 = LSM9DS1(i2c_y, dev_acc_sel=0x6A, dev_gyr_sel=0x6A, dev_mag_sel=0x1C)

        # Start periodic measurements as thread
        _thread.start_new_thread(self._run, ())

    def _run(self):
        while True:
            acc = self._lsm9d1.accel.xyz()
            self._r = min(int(acc[1] * 512), 255) if acc[1] > 0 else 0
            self._g = min(int(-acc[1] * 512), 255) if acc[1] < 0 else 0
            self._led_tile.set_color(self._r, self._g, 0)

    def get_latest_measurement_rgb(self):
        return self._r, self._g, 0


class AccessPoint(network.WLAN):
    SSID = "Guild42Mp"

    def __init__(self):
        super().__init__(1)
        self.config(essid=self.SSID)  # set AP SSID
        self.config(channel=4)  # set AP channel
        self.active(1)  # enable the AP
        print("Started Access point: %s" % self.SSID)


class DemoWebServer:
    def __init__(self, web_path, measurement_source):
        self.measurement_source = measurement_source

        self.srv = MicroWebSrv(webPath=web_path)
        self.srv.MaxWebSocketRecvLen = 256
        self.srv.WebSocketThreaded = False
        self.srv.AcceptWebSocketCallback = self._accept_websocket_callback
        self.srv.Start()

    def _accept_websocket_callback(self, websocket, httpclient):
        print("Accepted Websocket Connection")
        websocket.RecvTextCallback = self._received_text_callback
        websocket.RecvBinaryCallback = self._received_binary_callback
        websocket.ClosedCallback = self._websocket_closed_callback
        # _thread.start_new_thread()

    def _received_text_callback(self, websocket, msg):
        if msg == "get":
            r, g, b = self.measurement_source.get_latest_measurement_rgb()
            websocket.SendText("%d,%d,%d" % (r, g, b))
        else:
            print("Received unexpected text on Websocket: " + msg)

    def _received_binary_callback(self, websocket, data):
        print("Received Data: %s" % data)

    def _websocket_closed_callback(self, websocket):
        print("Websocket closed.")


if __name__ == "__main__":
    tile = LedTile()
    meas = ThreadedMeasuring(tile)
    ap = AccessPoint()
    DemoWebServer('www/', meas)
