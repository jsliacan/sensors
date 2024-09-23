#!/usr/bin/env python3

"""
Ultrasound Maxbotix sensor
"""

import argparse
import datetime
import logging

import RPi.GPIO as GPIO
import smbus2 as smbus

from time import sleep

from BicycleSensor import BicycleSensor, configure_logging

class UltrasoundSensor(BicycleSensor):

  def __init__(self, name, hash, measurement_frequency, upload_interval, logger):
    BicycleSensor.__init__(self, name, hash, measurement_frequency, upload_interval)

    self.ADDRESS = 0x70
    self.PIN = 4 # GPIO numbering of the orange wire; plug it into GPIO pin 4
    
    GPIO.setmode(GPIO.BCM) # set up BCM (GPIO) numbering
    GPIO.setup(self.PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set GPIO 4 as input
  
  def take_range(self):

    smbus(1).write_byte(self.ADDRESS, 0x51) # Write the sensor's address and the range command, 0x51
    #sleep(0.1) # Allow the sensor to process the readings with a ~100mS delay

  def report_range(self):

    latest_range = smbus(1).read_word_data(self.ADDRESS, 0xFF) # a command (0xFF) is required by syntax not the part
    return str(((latest_range & 0xFF) << 8) + (latest_range >> 8)) # distance reading in cm (as a string)

  def write_header(self):
    '''Override to write the header to the CSV file.'''
    logging.info("Writing a header to file...")
    self.write_to_file("date,time,distance")

  def write_measurement(self):
    """
    Override to write measurement data to the CSV file.
    
    This function is called at 200Hz frequency. Each time, it waits till orange
    pin is low and only then returns a reading. In effect, it's an adaptive
    frequency with 1/200s precision.
    """
    
    self.take_range(self.address)
    distance = 0
    while True:
      if GPIO.input(self.PIN): # if GPIO port 4 is On/1/True/High
        logger.info("Port " + str(self.PIN) + "is 1/GPIO.HIGH/True")
      else:
        logger.info("Port " + str(self.PIN) + "is 0/GPIO.LOW/False")
        self.report_range(self.address)
        distance = self.take_range(self.address)

        # write record to data file 
        datestamp, timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f").split(" ")
        logger.info("timestamp: " + timestamp + ", distance: " + distance)
        data_row = f"{datestamp},{timestamp},{distance}"
        self.write_to_file(data_row)

        break # return


if __name__ == '__main__':

  PARSER = argparse.ArgumentParser(
    description='Ultrasound Sensor',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )

  PARSER.add_argument('--hash', type=str, required=True, help='[required] hash of the device')
  PARSER.add_argument('--name', type=str, default="VTIUltrasound", help='[required] name of the sensor')
  PARSER.add_argument('--loglevel', type=str, default='DEBUG', help='Set the logging level (e.g., DEBUG, INFO, WARNING)')
  PARSER.add_argument('--measurement-frequency', type=float, default=200.0, help='Frequency of sensor measurements in 1/s')
  PARSER.add_argument('--stdout', action='store_true', help='Enables logging to stdout')
  PARSER.add_argument('--upload-interval', type=float, default=300.0, help='Interval between uploads in seconds')
  ARGS = PARSER.parse_args()

  # Configure logging
  logger = configure_logging(stdout=ARGS.stdout, rotating=True, loglevel=ARGS.loglevel, logfile="VTIUltrasound.log")

  ultrasound_sensor = UltrasoundSensor(ARGS.name, ARGS.hash, ARGS.measurement_frequency, ARGS.upload_interval, logger)
  ultrasound_sensor.main()
