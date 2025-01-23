import argparse
import csv
import logging
import os
import shutil
import signal
import sys
import threading
import time
import traceback
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests   # type: ignore


def configure_logging(stdout: bool = True, rotating: bool = False, loglevel: str = 'INFO', logfile: str = 'sensor_template.log') -> logging.Logger:
  '''Configure logging.'''

  log_dir = 'log'
  filename = logfile

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

  # Log the command-line arguments
  logging.getLogger().info(f'Command-line arguments: {sys.argv[1:]}')

  return logging.getLogger()


class BicycleSensor(ABC):
  def __init__(self, name, hash, measurement_frequency, upload_interval):
    self._name = name
    self._hash = hash
    self._measurement_frequency = measurement_frequency
    self._upload_interval = upload_interval
    self._alive = True

    # Create necessary directories
    os.makedirs('pending', exist_ok=True)
    os.makedirs('uploaded', exist_ok=True)

    # Initialize the upload queue
    self._upload_queue = deque(sorted([os.path.join('pending', f) for f in os.listdir('pending') if os.path.isfile(os.path.join('pending', f))]))

    self._file = None
    self.upload_event = threading.Event()
    self.upload_thread = threading.Thread(target=self._upload_data_loop)
    self.upload_thread.start()

    # Handle termination signals
    signal.signal(signal.SIGTERM, self._handle_shutdown)
    signal.signal(signal.SIGINT, self._handle_shutdown)

    self.trigger_upload()

  @abstractmethod
  def write_header(self):
    '''Abstract method to write the header to the CSV file.'''
    pass

  @abstractmethod
  def write_measurement(self):
    '''Abstract method to write measurement data to the CSV file.'''
    pass

  def write_to_file(self, data: str):
    '''Helper method to write data to the file.'''
    if self._file:
      self._file.write(data)
      self._file.write('\n')

  def _handle_shutdown(self, signum, frame):
    '''Gracefully handle shutdown signals.'''
    self._alive = False
    self.upload_event.set()  # Ensure thread wakes up to check _alive flag
    logging.warning(f'Shutdown due to signal {signum}')

  def trigger_upload(self):
    '''Trigger the upload event.'''
    if self._file:
      self._file.close()
      self._file = None
      self._upload_queue.append(self._filename)

    self._filename = os.path.join('pending', datetime.now().strftime('%Y%m%d_%H%M%S.csv'))

    if self._alive:
      try:
        self._file = open(self._filename, 'w')
        self.write_header()
        logging.info(f"New file '{self._filename}' created")
      except IOError as e:
        logging.error(f"Error opening file '{self._filename}': {e}")
        self._file = None
    self.upload_event.set()

  def _upload_data_loop(self):
    '''The main loop that runs in a separate thread to handle data uploads.'''
    while self._alive:
      self.upload_event.wait()  # Wait until the event is set
      self._upload_data()       # Perform the upload
      self.upload_event.clear() # Reset the event to pause the thread

    # Final upload after shutdown
    logging.warning('Upload thread stopped - final upload attempt')
    self.trigger_upload()
    self._upload_data()
    logging.warning('Upload thread stopped')

  def _upload_data(self):
    '''Perform the data upload to the server.'''
    try:
      while self._upload_queue:
        filename = self._upload_queue[0]

        # Make sure to format USB device as ext4 and put a filesystem on it. The
        # code expects the USB to be `bikedata` and mounts to
        # `/media/vti/bikedata` on the RPi.
    
        # I used Disk Utility on Fedora and once I formatted the USB disk I
        # created a partition called `bikedata` on it (ext4 type). That's it.
        
        # Write data to USB drive as a backup
        usb_path = os.path.join("/", "media", "vti", "bikedata")
        print(usb_path, flush=True)
        
        if os.path.exists(usb_path):
          print("usb_path exists!")
          sensor_usb_path = os.path.join(usb_path, self._name)
          if not os.path.exists(sensor_usb_path):
            os.makedirs(sensor_usb_path)
            print("make sensor_usb_path")
          shutil.copyfile(filename, os.path.join(sensor_usb_path, filename.split("/")[-1]))
        
       
        with open(filename, 'r') as file:
          csv_data = file.readlines()

        r = requests.post('https://bicycledata.vti.se/api/sensor/update', json={'hash': self._hash, 'sensor': self._name, 'csv_data': csv_data}, timeout=10)
        logging.info(f'{r.status_code}: {filename}')

        if r.status_code == 200:
          shutil.move(filename, 'uploaded')
          self._upload_queue.popleft()
        else:
          logging.info(r.text.strip())
          break
    except Exception as e:
      logging.error("Something went wrong during the upload process")
      logging.error(traceback.format_exc())

  def main(self):
    '''Main loop for handling sensor measurements and triggering uploads.'''
    _time = time.time()

    while self._alive:
      try:
        self.write_measurement()

        current_time = time.time()
        if current_time - _time >= self._upload_interval:
          _time = current_time
          self.trigger_upload()

        time.sleep(1.0 / self._measurement_frequency)
      except Exception as e:
        logging.error(f"Error during main loop: {e}")
        logging.error(traceback.format_exc())

    # Trigger final upload and clean up
    if self._file:
      self.trigger_upload()

    # Wait for the upload thread to finish
    self.upload_thread.join()
    logging.warning('Process stopped')
