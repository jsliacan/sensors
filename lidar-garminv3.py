#!/usr/bin/env python3

"""
  1. Capacitor technically not needed between Vcc and Ground:
  https://support.garmin.com/en-US/?faq=tma27PcpYS2A8etp7EB259

  "The purpose of including an electrolytic capacitor when wiring a LIDAR-Lite
  v3 is to ensure that when LLV3 is connected to a power source that may have
  limited maximum current capacity, such as a computer's USB port, that the
  power on current draw of the sensor doesn’t cause the power source to go into
  an over-current mode and possibly shut down.  In some instances, when there
  is a robust external power source for example, there may not be a need to
  install this capacitor in the circuit.  When in doubt, the capacitor is
  advisable.  The size of the capacitor can be in the range of 330µF to
  1000µF."

  2. Readings of 1cm and 5cm:
  https://support.garmin.com/en-US/?faq=Y4baLgCOOY0LR7dSW0DG09
  - 1cm : no return signal
  - 5cm : invalid measurement condition


  - A reading of 1cm on the LIDAR-Lite v3 sensor is an indication of no return
    signal.
  - A reading of 5cm is an indication of an invalid measurement condition which
    can happen for a variety of reasons.
"""

import argparse
import asyncio
import logging
import smbus2 as smbus
import datetime, time

from BicycleSensor import BicycleSensor, configure_logging

SENSOR_NAME="VTIGarminLidarLiteV3"

class LidarSensor(BicycleSensor):

  def __init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread):
    BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval, use_worker_thread)

    self.BUS = 1 # on RPi5, it's bus no.1 - can check with `ls /dev/*i2c*`
    self.ADDRESS = 0x62 # get with `sudo i2cdetect -y 1`
    self.DISTANCE_WRITE_REGISTER = 0x00
    self.DISTANCE_WRITE_VALUE = 0x04
    self.DISTANCE_READ_REGISTER_1 = 0x8f
    self.DISTANCE_READ_REGISTER_2 = 0x10

    try:
      self.actual_bus = smbus.SMBus(self.BUS)
    except:
      logging.error(f"Not able ot instantiate bus number {self.BUS}")
      raise

  def writeAndWait(self):
    self.actual_bus.write_byte_data(self.ADDRESS, self.DISTANCE_WRITE_REGISTER, self.DISTANCE_WRITE_VALUE);
    #time.sleep(0.01)

  def readDistAndWait(self):
    reading = self.actual_bus.read_i2c_block_data(self.ADDRESS, self.DISTANCE_READ_REGISTER_1, 2)
    # time.sleep(0.01)
    return (reading[0] << 8 | reading[1])

  def getDistance(self):
    self.writeAndWait()
    dist = self.readDistAndWait()
    return dist # in cm

  def write_header(self):
    '''Override to write the header to the CSV file.'''
    logging.info("Writing a header to file...")
    self.write_to_file("unix_timestamp,datetime,distance")

  def write_measurement(self):
    '''Override to write measurement data to the CSV file.'''
    distance = str(self.getDistance()) # in cm
    dt = datetime.datetime.now()
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    dt_unix = dt.timestamp()
    logging.info("timestamp: " + dt_str)
    data_row = f"{dt_unix},{dt_str},{distance}"
    self.write_to_file(data_row)

  async def worker_main(self):
      pass 

if __name__ == '__main__':

  PARSER = argparse.ArgumentParser(
    description='Lidar Sensor',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )

  PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
  PARSER.add_argument('--name', type=str, default=SENSOR_NAME, help='[required] name of the sensor')
  PARSER.add_argument('--loglevel', type=str, default='DEBUG', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
  PARSER.add_argument('--measurement-frequency', type=float, default=50.0, help='Frequency of sensor measurements in 1/s')
  PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
  PARSER.add_argument('--upload-interval', type=float, default=300.0, help='Interval between uploads in seconds')
  PARSER.add_argument('--use_worker_thread', type=bool, default=False, help='Use a background thread for worker process or not')
  ARGS = PARSER.parse_args()

  # Configure logging
  configure_logging(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel, logfile=f"{SENSOR_NAME}.log")

  lidar_sensor = LidarSensor(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval, ARGS.use_worker_thread)
  lidar_sensor.main()
