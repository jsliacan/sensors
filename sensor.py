#!/usr/bin/env python3

import argparse
import random
import time
from datetime import datetime

from BicycleSensor import BicycleSensor, configure


class SensorTemplate(BicycleSensor):
  '''Example subclass that implements the abstract methods of BicycleSensor.'''

  def write_header(self):
    '''Write the CSV header.'''
    return 'timestamp,button'

  def write_measurement(self, data=None):
    '''Handle both periodic and event-based measurements.'''
    timestamp = datetime.now().isoformat()
    event_type = 1 if data else 0
    self.data_buffer.append(f"{timestamp},{event_type}")

  def background_worker(self):
    '''Return the function to run in the background thread.'''
    def worker():
      while self.alive:
        time.sleep(random.uniform(1, 3))  # Random interval between button presses
        self.write_measurement(data=True)  # Simulate a button press event
    return worker

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

  # Instantiate and run the sensor
  sensor = SensorTemplate(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval)
  sensor.main()
