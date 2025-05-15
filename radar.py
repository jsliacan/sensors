#!/usr/bin/env python3

"""
Garmin Varia Radar RCT716

- Address: "F2:ED:49:D5:26:ED" with name "RCT716-19942" or similar
- Characteristic UUID: "6A4E3203-667B-11E3-949A-0800200C9A66", handle: 188 (int)

Target encoding

Name    |   Type    | min val   | max val   |
---------------------------------------------
info    |   uint8   |   0       |   255     | <-- first 6 bits is target ID (64 unique)
range   |   uint8   |   0       |   255     | <-- unit: meters
speed   |   uint8   |   0       |   63.75   | <-- unit: m/s  resolution: 0.25


Characteristic encoding
(if no exception, then below)
bytes   |  Field
------------------
0       | <flags> 
1       | <target0>
2       | <target0>
3       | <target0>
4       | <target1>
5       | <target1>
6       | <target1>
...
16      | <target5>
17      | <target6>
18      | <target7>
19      | <reserved>
(if exception occurs, then byte 1 is <exception> and rest is empty)
(if more than 6 cars -- up to 8 -- then the remaining come in a new
characteristic usually within 0.1s)
"""

import argparse
import asyncio
import logging
import smbus2 as smbus
import datetime, time

from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic

from BicycleSensor import BicycleSensor, configure_logging

def bin2dec(n):
    """
    Convert floating point binary (exponent=-2) to decimal float.
    """
    fractional_part = 0.0
    if n & 1 > 0:
        fractional_part += 0.25
    if n & 2 > 0:
        fractional_part += 0.5
    return fractional_part + (n>>2)

def notification_handler(characteristic: BleakGATTCharacteristic, data: bytearray):
    """
    Simple notification handler which processes the data received into a
    CSV row and prints it into a file.
    """
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    logging.info("timestamp: " + timestamp)
    target_id_mask = 0b11111100 # mask that reveals first 6 bits; use '&' with value
    target_ids = [0 for x in range(6)]
    target_ranges = [0 for x in range(6)] # 6 targets, each 3 bytes (info, range, speed)
    target_speeds = [0.0 for x in range(6)]
    bin_target_speeds = ["" for x in range(6)]

    # data is a bytearray
    intdata = [x for x in data]
    j = 0 # target index
    for i, dat in enumerate(intdata[1:]): # ignore flags in pos 0
        if i%3 == 0: # each target has 3 bytes
            j = i//3
            target_ids[j] = (dat & target_id_mask)
        elif i%3 == 1:
            target_ranges[j] = dat
        else: 
            target_speeds[j] = bin2dec(dat)
            bin_target_speeds[j] = format(dat, '08b')

    data_row = f"{timestamp}\t{target_ids}\t{target_ranges}\t{target_speeds}\t{bin_target_speeds}\n"
    self.write_to_file(data_row)

async def radar(device_address, characteristic_uuid, notification_callback):
    """
    Main radar function that coordinates communication with Varia radar.
    """

    varia = await BleakScanner.find_device_by_address(address)
    
    if varia is None:
        print("Could not find device with %s", address)
        return

    async with BleakClient(varia) as client:
        print("Connected.", flush=True)
        
        await client.start_notify(characteristic_uuid, notification_callback)
        # await asyncio.sleep(60.0)     # run for given time (in seconds)
        await asyncio.Future()  # run indefinitely
        # await client.stop_notify(RADAR_CHAR_UUID)  # use with asyncio.sleep()

class RadarSensor(BicycleSensor):

    def __init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread):
        BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread)

        self.ADDRESS = "F2:ED:49:D5:26:ED"
        self.CHAR_UUID = "6a4e3203-667b-11e3-949a-0800200c9a66" 
    
    def write_header(self):
        '''Override to write the header to the CSV file.'''
        
        logging.info("Writing a header to file...")
        self.write_to_file("datetime,target_ids,target_ranges,target_speeds,bin_target_speeds")

    def write_measurement(self):
        pass 

    def worker_main(self):
        """
        Implementation of the function that runs in the worker thread.
        """
        asyncio.run(radar(self.ADDRESS, self.CHAR_UUID, notification_handler))

if __name__ == '__main__':

    PARSER = argparse.ArgumentParser(
        description='Radar Sensor',
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
    PARSER.add_argument('--name', type=str, default="VTIGarminVariaRCT716", help='[required] name of the sensor')
    PARSER.add_argument('--loglevel', type=str, default='DEBUG', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
    PARSER.add_argument('--measurement-frequency', type=float, default=1.0, help='Not utilized')
    PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
    PARSER.add_argument('--upload-interval', type=float, default=5.0, help='Interval between uploads in seconds')
    PARSER.add_argument('--use_worker_thread', type=bool, default=True, help='Use a background thread for worker process or not')
    ARGS = PARSER.parse_args()

# Configure logging
    configure_logging(stdout=ARGS.stdout,
                      rotating=True,
                      loglevel=ARGS.loglevel,
                      logfile="VTIGarminVariaRCT716.log")

    radar_sensor = RadarSensor(ARGS.name,
                               ARGS.hash,
                               ARGS.measurement_frequency,
                               ARGS.upload_interval,
                               ARGS.use_worker_thread)
    radar_sensor.main()
