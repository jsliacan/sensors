#!/usr/bin/env python3

"""
Garmin Varia Radar RCT716

- Address: such as "C1:1A:18:51:69:FC" with name "RCT716-23011" (radar+camera+light)
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

SENSOR_NAME="VTIGarminVariaRCT23011"
SENSOR_ADDRESS="C1:1A:18:51:69:FC"

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


class RadarSensor(BicycleSensor):

    def __init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread):
        
        self.ADDRESS = SENSOR_ADDRESS
        self.CHAR_UUID = "6a4e3203-667b-11e3-949a-0800200c9a66" # same for all Varias
        
        BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread)

    
    def write_header(self):
        '''Override to write the header to the CSV file.'''
        
        logging.info("Writing a header to file...")
        self.write_to_file("unix_timestamp\tdatetime\ttarget_ids\ttarget_ranges\ttarget_speeds\tbin_target_speeds")

    def write_measurement(self):
        pass 

    def worker_main(self):
        """
        Implementation of the function that runs in the worker thread.
        """
        asyncio.run(self.radar())

    def notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        """
        Simple notification handler which processes the data received into a
        CSV row and prints it into a file.
        """
        
        dt = datetime.datetime.now()
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        dt_unix = dt.timestamp()
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

        data_row = f"{dt_unix}\t{dt_str}\t{target_ids}\t{target_ranges}\t{target_speeds}\t{bin_target_speeds}"
        logging.info(data_row)
        self.write_to_file(data_row)

    async def radar(self):
        """
        Main radar function that coordinates communication with Varia radar.
        """

        varia = await BleakScanner.find_device_by_address(self.ADDRESS)
        
        if varia is None:
            logging.warning("Could not find device with %s", self.ADDRESS)
            return

        async with BleakClient(varia) as client:
            logging.info("Connected.")
            
            await client.start_notify(self.CHAR_UUID, self.notification_handler)
            # await asyncio.sleep(60.0)     # run for given time (in seconds)
            await asyncio.Future()  # run indefinitely
            # await client.stop_notify(RADAR_CHAR_UUID)  # use with asyncio.sleep()


if __name__ == '__main__':

    PARSER = argparse.ArgumentParser(
        description='Radar Sensor',
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
    PARSER.add_argument('--name', type=str, default=SENSOR_NAME, help='[required] name of the sensor')
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
                      logfile=f"{SENSOR_NAME}.log")

    radar_sensor = RadarSensor(ARGS.name,
                               ARGS.hash,
                               ARGS.measurement_frequency,
                               ARGS.upload_interval,
                               ARGS.use_worker_thread)
    radar_sensor.main()
