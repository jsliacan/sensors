#!/usr/bin/env python3

"""
  Purpose:
    Delimit the start of each ride ("session").
"""

import argparse
import asyncio
import logging
import datetime, time


from BicycleSensor import BicycleSensor, configure_logging

SENSOR_NAME="Session"
UPLOAD_INTERVAL=5.0 # in seconds
EPSILON=0.01

class SessionSensor(BicycleSensor):

    def __init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread):
        
        self.START = datetime.datetime.now()
        self.DELTA = datetime.timedelta(seconds=int(UPLOAD_INTERVAL))
        
        BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread)

    async def worker_main(self):
        pass 

    def write_header(self):
        '''Override to write the header to the CSV file.'''
        rn = datetime.datetime.now()
        if rn - self.START < self.DELTA:
            logging.info("Writing a header to file...")
            self.write_to_file("unix_timestamp\tdatetime")

    def write_measurement(self):
        '''Override to write measurement data to the CSV file.'''
        rn = datetime.datetime.now()
        # only write into file 1x after box turns on.
        if rn - self.START < self.DELTA:
            dt_str = self.START.strftime("%Y-%m-%d %H:%M:%S.%f")
            dt_unix = self.START.timestamp()
            logging.info("timestamp: " + dt_str)
            data_row = f"{dt_unix}\t{dt_str}"
            self.write_to_file(data_row)

if __name__ == '__main__':

    PARSER = argparse.ArgumentParser(
        description='Session Sensor',
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
    PARSER.add_argument('--name', type=str, default=SENSOR_NAME, help='[required] name of the sensor')
    PARSER.add_argument('--loglevel', type=str, default='DEBUG', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
    PARSER.add_argument('--measurement-frequency', type=float, default=1/UPLOAD_INTERVAL-EPSILON, help='Frequency of sensor measurements in 1/s')
    PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
    PARSER.add_argument('--upload-interval', type=float, default=UPLOAD_INTERVAL, help='Interval between uploads in seconds')
    PARSER.add_argument('--use_worker_thread', type=bool, default=False, help='Use a background thread for worker process or not')
    ARGS = PARSER.parse_args()

# Configure logging
    configure_logging(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel, logfile=f"{SENSOR_NAME}.log")

    session_sensor = SessionSensor(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval, ARGS.use_worker_thread)
    session_sensor.main()
