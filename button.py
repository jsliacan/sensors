#!/usr/bin/env python3

"""
  Good resource: https://raspi.tv/2013/rpi-gpio-basics-4-setting-up-rpi-gpio-numbering-systems-and-inputs

  Purpose:
    Monitor a button press.

  Note:
    Use GPIO22 pin and the neighbouring 3V3 pin.

    If you wire the switch between a GPIO pin and ground then in software you
    would need to set a pull-up on the GPIO pin so that when the switch is
    pressed then the GPIO pin will be pull-down. So while the switch is not
    pressed you GPIO input would return a 1 or true, and when pressed it would
    return a 0 or false.

    If you wire the switch between a GPIO pin and 3.3v then you would need to
    set a pull-down in software so that when you switch is pressed then the
    GPIO pin will be pull-up. So while the switch is not pressed you GPIO input
    would return a 0 or false, and when pressed it would return a 1 or true.
"""

import argparse
import logging
import datetime, time

import RPi.GPIO as GPIO   # type: ignore

from BicycleSensor import BicycleSensor, configure_logging

class ButtonSensor(BicycleSensor):

  def __init__(self, name, hash, measurement_frequency, upload_interval):
    BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval)
    
    self.PIN = 22                                                 # use GPIO 22

    GPIO.setmode(GPIO.BCM)                                        # use GPIO numbering
    GPIO.setup(self.PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)     # set GPIO 22 as input

  def write_header(self):
    '''Override to write the header to the CSV file.'''
    logging.info("Writing a header to file...")
    self.write_to_file("date,time,button")

  def write_measurement(self):
    '''Override to write measurement data to the CSV file.'''
    datestamp, timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f").split(" ")
    logging.info("timestamp: " + timestamp)
    data_row = f"{datestamp},{timestamp},{1 if GPIO.input(self.PIN) else 0}"
    self.write_to_file(data_row)

if __name__ == '__main__':

  PARSER = argparse.ArgumentParser(
    description='Button Sensor',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )

  PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
  PARSER.add_argument('--name', type=str, default="VTIButton", help='[required] name of the sensor')
  PARSER.add_argument('--loglevel', type=str, default='DEBUG', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
  PARSER.add_argument('--measurement-frequency', type=float, default=50.0, help='Frequency of sensor measurements in 1/s')
  PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
  PARSER.add_argument('--upload-interval', type=float, default=5.0, help='Interval between uploads in seconds')
  ARGS = PARSER.parse_args()

  # Configure logging
  configure_logging(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel, logfile="VTIButton.log")

  button_sensor = ButtonSensor(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval)
  button_sensor.main()