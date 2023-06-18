from machine import Pin, I2C, RTC, UART
from time import sleep
import json
import re
import _thread

# Secret file test

import network
import urequests

import time
import ntptime

from dht import DHT22
from bmp280 import BMP280, BMP280_CASE_WEATHER
import bme280
import sds011

with open('config.json', 'r') as f:
    config = json.load(f)
    f.close()

def connect():
    time.sleep(10)
    station = network.WLAN(network.STA_IF)
    station.active(True)
    if station.isconnected() == True:
        print('Network connection already established!')
        return
    print(config['ssid'], config['password'])
    station.connect(config['ssid'], config['password'])
    while station.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = station.ifconfig()[0]
    print(f'Connected on {ip}')

print('Establishing network connection...')
connect()

def _otaUpdate():
    print('Checking for Updates...')
    from ota_updater import OTAUpdater
    updated = True
    try:
        otaUpdater = OTAUpdater('https://github.com/lmg-anrath/weatherstation-client-pico', main_dir="/")
        updated = otaUpdater.install_update_if_available()
        del(otaUpdater)
    except OSError as e:
        machine.reset()
    if updated:
        machine.reset()
    else:
        print("No new update")

try:
    ntptime.settime()
except OSError as e:
    machine.reset()

_otaUpdate()

print('Loading sensors...')

sdsUse = True
try:
    uart = UART(1, baudrate=9600, rx=Pin(9), tx=Pin(8))
    sds = sds011.SDS011(uart)
    sds.wake()
except OSError as e:
    sdsUse = False
    print('SDS Sensor Loading failed!')

dhtUse = True
try:
    pin = Pin(15, Pin.IN, Pin.PULL_UP)
    sensor = DHT22(pin)
except OSError as e:
    dhtUse = False
    print('DHT11 Sensor Loading failed!')

bmpUse = True
try:
    bus = I2C(0,sda=Pin(20), scl=Pin(21), freq=400000)
    bmp = bme280.BME280(i2c=bus)
except OSError as e:
    bmpUse = False
    print(e)
    print('BMP280 Sensor Loading failed!')

print('Successfully loaded all sensors.')

sleep(25)

runs = 0
while True:
            
    (year, month, day, hour, minute, second, wday, yday) = time.localtime()
    wait_time = ((minute // 15 + 1) * 15 - minute) * 60 - second
    print('Waiting %s seconds...' %wait_time)
    #time.sleep(wait_time)
    sleep(30)
    
    timestamp = str(round(time.time()))
    upload = True
    print('')
    (year, month, day, hour, minute, second, wday, yday) = time.localtime()
    print(f'{year}-{month}-{day} {hour}:{minute}:{second}')
    
    print('Reading data...')
    if dhtUse:
        print('-- DHT11 Sensor --')
        try:
            sensor.measure()
            t = sensor.temperature()
            h = sensor.humidity()
            print('(Temperature: %3.1f C)' %t)
            print('Humidity: %3.1f %%' %h)
        except OSError as e:
            print('DHT11 Sensor Reading failed!')
    if bmpUse:
        print('-- BMP280 Sensor --')
        try:
            t = bmp.values[0]
            p = bmp.values[1]
            print('Temperature: %3.1f C' %t)
            print('Pressure: %3.2f hPa' %p)
        except OSError as e:
            print('BMP280 Sensor Reading failed!')
    if sdsUse:
        print('-- SDS011 Sensor --')
        status = sds.read()
        pkt_status = sds.packet_status
        if(status == False):
            print('Measurement failed.')
        elif(pkt_status == False):
            print('Received corrupted data.')
        else:
            a25 = sds.pm25
            a10 = sds.pm10
            print('PM25:', sds.pm25)
            print('PM10:', sds.pm10)
            
    print('Finished reading data.')
    data = {
        'timestamp': timestamp,
    }
    
    if 't' in locals():
        data['temperature'] = t
        
    if 'h' in locals():
        data['humidity'] = h
        
    if 'p' in locals():
        data['air_pressure'] = p
        
    if 'a25' in locals():
        data['air_particle_pm25'] = a25
        
    if 'a10' in locals():
        data['air_particle_pm10'] = a10
    
    print('Uploading data...')
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': config['accessToken']
    }
    
    try:
        res = urequests.post(config['url'] + '/v2/stations/' + str(config['stationId']), data = json.dumps(data), headers = headers)
        print('Upload completed with status code %s!' %res.status_code)
        print('Response from server: ' + res.text)
        res.close()
    except OSError as e:
        machine.reset()
    runs = runs + 1
    _otaUpdate()
    if (runs >= 24):
        machine.reset()
