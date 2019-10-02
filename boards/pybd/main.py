
import network
from microWebSrv import MicroWebSrv

from led36 import led36
from sensa import OPT3001
import pyb
import time 
import machine
from lps22hx import LPS22HH
from lsm9ds1 import LSM9DS1
import time
import _thread

class MeasurementAcquire:
    def __init__(self):
        config = {
            'lps22hh': {'i2c_bus': 2, 'i2c_addr': 0x5C},
            'lsm9ds1_accgyr': {'i2c_bus': 2, 'i2c_addr': 0x6A},
            'lsm9ds1_mag': {'i2c_bus': 2, 'i2c_addr': 0x1C},
            'extPower': {'enable': "EN_3V3"},
        }

        pon = pyb.Pin(config['extPower']['enable'])
        pon.on()
        time.sleep_ms(20)

        self.tile = led36()
        pyb.Pin('PULL_SCL', pyb.Pin.OUT, value=1)  # enable 5.6kOhm X9/SCL pull-up
        pyb.Pin('PULL_SDA', pyb.Pin.OUT, value=1)  # enable 5.6kOhm X10/SDA pull-up
        # i2cx = machine.I2C('X')
        i2cy = pyb.I2C(config['lps22hh']['i2c_bus'], pyb.I2C.MASTER, baudrate=100000)
        # lps22 = LPS22HH(i2cy, config['lps22hh']['i2c_addr'])
        self.lsm9d1 = LSM9DS1(i2cy, config['lsm9ds1_accgyr']['i2c_addr'], config['lsm9ds1_accgyr']['i2c_addr'],
                         config['lsm9ds1_mag']['i2c_addr'])
        self.tile.brightness(100)
        self.tile.fill_rgb(255, 255, 255)
        # sense = OPT3001(i2cx)

        _thread.start_new_thread(self.run, ())

    def run(self):
        while (True):
            acc = self.lsm9d1.accel.xyz()
            self.r = int(acc[1] * 512) if acc[1] > 0 else 0
            self.g = int(-acc[1] * 512) if acc[1] < 0 else 0
            self.tile.illu(self.r, self.g, 0)

    def get_latest_measurements(self):
        return self.r, self.g

# --- Webserver ---

class AccessPoint(network.WLAN):
    SSID = "Guild42Mp"
    PASSWORD="mp1234"
    
    def __init__(self):
        super().__init__(1)
        self.config(essid=self.SSID)          # set AP SSID
        self.config(password=self.PASSWORD)   # set AP password
        self.config(channel=4)             # set AP channel
        self.active(1)                     # enable the AP
        print("Started Access point: %s" % (self.SSID))

    def __del__(self):
        self.status('stations')    # get a list of connection stations
        self.active(0)             # shut down the AP

# ----------------------------------------------------------------------------

def _acceptWebSocketCallback(webSocket, httpClient):
    print("WS ACCEPT2")
    webSocket.RecvTextCallback   = _recvTextCallback
    webSocket.RecvBinaryCallback = _recvBinaryCallback
    webSocket.ClosedCallback     = _closedCallback

def _recvTextCallback(webSocket, msg) : 
    print("WS RECV TEXT : %s" % msg)
    r, g = meas.get_latest_measurements()
    webSocket.SendText("%d,%d,0" % (r, g))

def _recvBinaryCallback(webSocket, data) :
    print("WS RECV DATA : %s" % data)

def _closedCallback(webSocket) :
    print("WS CLOSED")
    run = False

meas = MeasurementAcquire()

ap  = AccessPoint()
srv = MicroWebSrv(webPath='www/')
srv.MaxWebSocketRecvLen     = 256
srv.WebSocketThreaded        = False
srv.AcceptWebSocketCallback = _acceptWebSocketCallback
srv.Start()

del ap

