#!/usr/bin/env python3

import argparse
import time

from BicycleSensor import BicycleSensor, configure


class SensorTemplate(BicycleSensor):
  '''Example subclass that implements the abstract methods of BicycleSensor.'''
  def write_header(self):
    '''Override to write the header to the CSV file.'''
    self.write_to_file('time')

  def write_measurement(self):
    '''Override to write measurement data to the CSV file.'''
    self.write_to_file(str(time.time()))


if __name__ == '__main__':
  PARSER = argparse.ArgumentParser(
    description='Sensor Template',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
  PARSER.add_argument('--name', type=str, required=True, help='[required] name of the sensor')
  PARSER.add_argument('--loglevel', type=str, default='INFO', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
  PARSER.add_argument('--measurement-frequency', type=float, default=1.0, help='Frequency of sensor measurements in 1/s')
  PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
  PARSER.add_argument('--upload-interval', type=float, default=300.0, help='Interval between uploads in seconds')
  ARGS = PARSER.parse_args()

  # Configure logging
  configure(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel)

  sensor = SensorTemplate(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval)
  sensor.main()
