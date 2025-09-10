#!/usr/bin/env python3

"""
    Lidar model: TF-Luna LiDAR Range Sensor (SKU: 24893)
    
    Wiki: https://www.waveshare.com/wiki/TF-Luna_LiDAR_Range_Sensor

    NOTE:
    =====
    Using 120Hz measurement-frequency because each time there is a 0.01s wait
    before taking a reading. So overall (with additional processing times) it
    works out to ~50Hz data frequency.
"""

import argparse
import logging
import smbus2 as smbus
import datetime, time

from BicycleSensor import BicycleSensor, configure_logging

class LidarSensor(BicycleSensor):

    def __init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread):
        BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread)

        self.BUS = 1 # on RPi5, it's bus no.1 - can check with `ls /dev/*i2c*`
        self.ADDRESS = 0x10 # get with `sudo i2cdetect -y 1`
        self.DATA_CMD = [0x5A,0x05,0x00,0x01,0x60] # Distance value instruction

        try:
            self.actual_bus = smbus.SMBus(self.BUS)
        except:
            logging.error(f"Not able ot instantiate bus number {self.BUS}")
            raise

    async def worker_main(self):
        pass 

    def get_data(self):
        self.actual_bus.write_i2c_block_data(self.ADDRESS, 0x00, self.DATA_CMD)
        time.sleep(0.01)
        data = self.actual_bus.read_i2c_block_data(self.ADDRESS, 0x00, 9)
        distance = data[0] | (data[1] << 8)
        strength = data[2] | (data[3] << 8)
        temperature = (data[4] | (data[5] << 8)) / 100 
        # print('distance = %5d cm, strength = %5d, temperature = %5d ℃'%(distance, strengh, temperature))
        return (distance, strength, temperature)


    def write_header(self):
        logging.info("writing a header to file...")
        self.write_to_file("unix_timestamp,datetime,distance,strength,temperature")

    def write_measurement(self):
        distance, strength, temperature = self.get_data()
        dt = datetime.datetime.now()
        # time.sleep(0.01)
        # create timestamp
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        dt_unix = dt.timestamp()
        logging.info("timestamp: " + dt_str)
        # write data
        data_row = f"{dt_unix},{dt_str},{distance},{strength},{temperature}"
        self.write_to_file(data_row)

if __name__ == '__main__':

    PARSER = argparse.ArgumentParser(
        description='Lidar Sensor',
        allow_abbrev=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
    PARSER.add_argument('--name', type=str, default="VTIGarminLidarLiteV3", help='[required] name of the sensor')
    PARSER.add_argument('--loglevel', type=str, default='DEBUG', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
    PARSER.add_argument('--measurement-frequency', type=float, default=120.0, help='Frequency of sensor measurements in 1/s')
    PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
    PARSER.add_argument('--upload-interval', type=float, default=300.0, help='Interval between uploads in seconds')
    PARSER.add_argument('--use_worker_thread', type=bool, default=False, help='Use a background thread for worker process or not')
    ARGS = PARSER.parse_args()

    # Configure logging
    configure_logging(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel, logfile="VTITFLunaLidar.log")

    lidar_sensor = LidarSensor(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval, ARGS.use_worker_thread)
    lidar_sensor.main()
