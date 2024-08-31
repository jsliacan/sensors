#!/usr/bin/env python3

import argparse
import logging
import os
import shutil
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests


def configure(stdout: bool = True, rotating: bool = False, loglevel: str = 'INFO') -> None:
  '''Configure logging.'''

  log_dir = 'log'
  filename = 'sensor_template.log'

  # Ensure the log directory exists
  if not os.path.isdir(log_dir):
    try:
      os.makedirs(log_dir)
    except OSError:
      raise Exception(f'Creation of the log directory "{log_dir}" failed')

  if not filename.endswith('.log'):
    filename += '.log'

  log_exists = os.path.isfile(os.path.join(log_dir, filename))

  log_file = os.path.join(log_dir, filename)

  # Formatter for logs
  log_format = '%(asctime)s: %(levelname)s [%(name)s] %(message)s'
  formatter = logging.Formatter(log_format)

  # Set up the appropriate log handler
  if rotating:
    handler = RotatingFileHandler(
      filename=log_file,
      mode='a',
      maxBytes=5 * 1024 * 1024,  # 5 MB
      backupCount=2
    )
    handler.setFormatter(formatter)

    # Roll over if the file already exists
    if log_exists:
      handler.doRollover()

    logging.getLogger().addHandler(handler)
  else:
    logging.basicConfig(
      filename=log_file,
      level=logging.INFO,
      format=log_format
    )

  # Optionally, log to stdout
  if stdout:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logging.getLogger().addHandler(stream_handler)

  # Convert log level string to numeric level
  numeric_level = getattr(logging, loglevel.upper(), None)
  if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {loglevel}")

  # Set the logging level for the root logger
  logging.getLogger().setLevel(numeric_level)

  # Log the version and command-line arguments
  logging.getLogger().info(f'Command-line arguments: {sys.argv[1:]}')


class Sensor:
  def __init__(self, name, hash, measurement_frequency, upload_interval):
    self._name = name
    self._hash = hash
    self._measurement_frequency = measurement_frequency
    self._upload_interval = upload_interval

    if not os.path.exists('pending'):
      os.makedirs('pending')

    if not os.path.exists('uploaded'):
      os.makedirs('uploaded')

    # In case there are some old files
    self._upload_queue = deque(sorted([os.path.join('pending', f) for f in os.listdir('pending') if os.path.isfile(os.path.join('pending', f))]))

    self._file = None

    # Initialize the upload thread
    self._alive = True
    self.upload_event = threading.Event()
    self.upload_thread = threading.Thread(target=self._upload_data_loop)
    #self.upload_thread.daemon = True
    self.upload_thread.start()

    self.trigger_upload()

  def trigger_upload(self):
    '''Trigger the upload event.'''
    if self._file:
      self._file.close()
      self._file = None
      self._upload_queue.append(self._filename)

    self._filename = 'pending/' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'

    try:
      self._file = open(self._filename, 'w')
      self._file.write('time\n')
      logging.info(f"New file '{self._filename}'")
    except IOError as e:
      logging.error(f"Error opening file '{self._filename}': {e}")
      self._file = None

    self.upload_event.set()

  def _upload_data_loop(self):
    '''The main loop that runs in a separate thread.'''
    while self._alive:
      self.upload_event.wait()  # Wait until the event is set
      self._upload_data()       # Perform the upload
      self.upload_event.clear() # Reset the event to pause the thread
    logging.warning('upload thread stopped')

  def _upload_data(self):
    try:
      while self._upload_queue:
        filename = self._upload_queue[0]

        with open(filename, 'r') as file:
          csv_data = file.readlines()

        r = requests.post('https://bicycledata.ochel.se:80/api/sensor/update', json={'hash': self._hash, 'sensor': self._name, 'csv_data': csv_data})
        logging.info(f'{r.status_code}: {filename}')

        if r.status_code == 200:
          shutil.move(filename, 'uploaded')
          self._upload_queue.popleft()
        else:
          break
    except Exception:
      logging.info(f'Something went wrong; we\'ll try later again')
      logging.error(traceback.format_exc())

  def main(self):
    _time = time.time()

    while self._alive:
      try:
        # Do Stuff HERE
        data = str(time.time())
        self._file.write(data + "\n")

        current_time = time.time()
        if current_time - _time >= self._upload_interval:
          _time = current_time
          self.trigger_upload()

        time.sleep(1.0/self._measurement_frequency)
      except Exception as e:
        logging.error(e)
        logging.error(traceback.format_exc())
      except KeyboardInterrupt:
        self._alive = False
        print('\r', end='')
        logging.warning('shutdown due to keyboard interrupt')

    if self._file:
      self.trigger_upload()
      self._file.close()

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
  PARSER.add_argument('--stdout', action='store_true', help='enables logging to stdout')
  PARSER.add_argument('--upload-interval', type=float, default=300.0, help='Interval between uploads in seconds')
  ARGS = PARSER.parse_args()

  # Configure logging
  configure(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel)

  sensor = Sensor(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval)
  sensor.main()

  logging.warning('Process stopped')
