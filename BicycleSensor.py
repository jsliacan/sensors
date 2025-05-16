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

import requests


def configure(stdout: bool = True, rotating: bool = False, loglevel: str = 'INFO', filename: str = 'sensor_template.log') -> None:
  log_dir = 'log'

  if not os.path.isdir(log_dir):
    os.makedirs(log_dir)

  if not filename.endswith('.log'):
    filename += '.log'

  log_exists = os.path.isfile(os.path.join(log_dir, filename))

  log_file = os.path.join(log_dir, filename)
  log_format = '%(asctime)s: %(levelname)s [%(name)s] %(message)s'
  formatter = logging.Formatter(log_format)

  if rotating:
    handler = RotatingFileHandler(
      filename=log_file,
      mode='a',
      maxBytes=5 * 1024 * 1024,
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

  if stdout:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logging.getLogger().addHandler(stream_handler)

  numeric_level = getattr(logging, loglevel.upper(), None)
  if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {loglevel}")

  logging.getLogger().setLevel(numeric_level)
  logging.getLogger().info(f'Command-line arguments: {sys.argv[1:]}')


class BicycleSensor(ABC):
  def __init__(self, name, hash, measurement_frequency, upload_interval):
    self._name = name
    self._hash = hash
    self._measurement_frequency = measurement_frequency
    self._upload_interval = upload_interval
    self.alive = True
    self.data_buffer = deque()

    os.makedirs('pending', exist_ok=True)
    os.makedirs('uploaded', exist_ok=True)

    self._upload_queue = deque(sorted([
      os.path.join('pending', f)
      for f in os.listdir('pending')
      if os.path.isfile(os.path.join('pending', f))
    ]))

    self.upload_event = threading.Event()

    signal.signal(signal.SIGTERM, self._handle_shutdown)
    signal.signal(signal.SIGINT, self._handle_shutdown)

    self.upload_thread = threading.Thread(target=self._upload_data_loop, daemon=True)
    self.upload_thread.start()

    self.trigger_upload()

    # Launch background worker, if implemented
    worker_func = self.background_worker()
    if callable(worker_func):
      self.custom_thread = threading.Thread(target=worker_func, daemon=True)
      self.custom_thread.start()
    else:
      self.custom_thread = None

  @abstractmethod
  def write_header(self) -> str:
    '''Abstract method to write the CSV header.'''
    pass

  @abstractmethod
  def write_measurement(self, data=None):
    '''Abstract method to collect a measurement.'''
    pass

  def background_worker(self):
    '''Override in subclass to provide event-based background logic.'''
    return None

  def _handle_shutdown(self, signum, frame):
    logging.warning(f'Shutdown signal received: {signum}')
    self.alive = False
    self.upload_event.set()

  def trigger_upload(self):
    '''Trigger a file rotation and queue current buffer for upload.'''
    if self.data_buffer:
      filename = os.path.join('pending', datetime.now().strftime('%Y%m%d_%H%M%S.csv'))
      try:
        file = open(filename, 'w')
        file.write(self.write_header() + '\n')
        logging.info(f"New file '{filename}' created")
      except IOError as e:
        logging.error(f"Error opening file '{filename}': {e}")
        return

      for line in self.data_buffer:
        file.write(line + '\n')
      self.data_buffer.clear()
      file.close()
      self._upload_queue.append(filename)

    self.upload_event.set()

  def _upload_data_loop(self):
    while self.alive:
      self.upload_event.wait()
      self._upload_data()
      self.upload_event.clear()

    # Final upload after shutdown
    logging.warning('Upload thread stopped - final upload attempt')
    self.trigger_upload()
    self._upload_data()
    logging.warning('Upload thread stopped')

  def _upload_data(self):
    try:
      while self._upload_queue:
        filename = self._upload_queue[0]

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
    except Exception:
      logging.error("Upload process error:")
      logging.error(traceback.format_exc())

  def main(self):
    next_upload_time = time.time() + self._upload_interval

    while self.alive:
      try:
        self.write_measurement()
        if time.time() >= next_upload_time:
          self.trigger_upload()
          next_upload_time = time.time() + self._upload_interval

        time.sleep(1.0 / self._measurement_frequency)
      except Exception:
        logging.error("Error in main loop:")
        logging.error(traceback.format_exc())

    self.upload_thread.join()
    if self.custom_thread:
      self.custom_thread.join()
    logging.warning('Sensor main loop stopped')
