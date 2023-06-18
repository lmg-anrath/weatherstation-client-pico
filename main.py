from machine import Pin, I2C, RTC, UART
from time import sleep
import json
import re

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

station = network.WLAN(network.STA_IF)
station.active(True)
def connect():
    if station.isconnected() == True:
        print('Network connection already established!')
        return
    station.active(True)
    station.connect(config['ssid'], config['password'])
    while station.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = station.ifconfig()[0]
    print(f'Connected on {ip}')
def disconnect():
    if station.active() == True:
        station.active(False)
    if station.isconnected() == False:
        print('Disconnected!')

print('Establishing network connection...')
connect()
ntptime.settime()

sleep(25)

while True:
            
    (year, month, day, hour, minute, second, wday, yday) = time.localtime()
    wait_time = ((minute // 15 + 1) * 15 - minute) * 60 - second
    print('Waiting %s seconds...' %wait_time)
    #time.sleep(wait_time)
    
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
            upload = False
    if bmpUse:
        print('-- BMP280 Sensor --')
        try:
            t = bmp.values[0]
            p = bmp.values[1]
            print('Temperature: %3.1f C' %t)
            print('Pressure: %3.2f hPa' %p)
        except OSError as e:
            print('BMP280 Sensor Reading failed!')
            upload = False
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
    if upload == False:
        print('Uploading failed due to insufficient data!')
        continue
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
        
    print(data)
    
    print('Uploading data...')
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': config['accessToken']
    }
    res = urequests.post(config['url'] + '/v2/stations/' + str(config['stationId']), data = json.dumps(data), headers = headers)
    print('Upload completed with status code %s!' %res.status_code)
    print('Response from server: ' + res.text)
    res.close()


"""
from machine import UART, Pin, I2C
import time
import sds011
from utime import sleep
from dht import DHT22
import bme280 

tx = Pin(8)
rx = Pin(9)

uart = UART(1, baudrate=9600, rx=rx, tx=tx)
dust_sensor = sds011.SDS011(uart)
dust_sensor.sleep()

sleep(1)
dht22_sensor = DHT22(Pin(15, Pin.IN, Pin.PULL_UP))

i2c=I2C(0,sda=Pin(20), scl=Pin(21), freq=400000)

err_num = 0

dust_sensor.wake()

time.sleep(10)

try:
    while True:
        #Datasheet says to wait for at least 30 seconds...
        #Returns NOK if no measurement found in reasonable time
        status = dust_sensor.read()
        #Returns NOK if checksum failed
        pkt_status = dust_sensor.packet_status
        #Stop fan
        dust_sensor.sleep()
        if(status == False):
            print('Measurement failed.')
            err_num = err_num + 1
        elif(pkt_status == False):
            print('Received corrupted data.')
            err_num = err_num + 1
        else:
            print('PM25:\t\t\t', dust_sensor.pm25)
            print('PM10:\t\t\t', dust_sensor.pm10)
            
        dht22_sensor.measure()
        temp = dht22_sensor.temperature()
        humi = dht22_sensor.humidity()
        # Werte ausgeben
        print('Temperatur:\t\t', temp, '°C')
        print('Luftfeuchtigkeit:\t', humi, '%')
        
        bme = bme280.BME280(i2c=i2c)          #BME280 object created
        print('Luftdruck:\t\t', bme.values[1])
        print()

        time.sleep(15)
except KeyboardInterrupt:
    print(err_num)"""