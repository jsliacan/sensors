# Ultrasound sensor

**Model**: _MB7040 I2CXLMaxSonar-WR - (-1XX) 3/4" NPS WR_; Housing: _Fluorosilicone_; Option: _(IP68)_

- [Wiring and connectors](https://maxbotix.com/pages/connection-details?_pos=1&_psq=connect&_ss=e&_v=1.0)
- [Information on GPIO pins on RPi](https://pinout.xyz/pinout/i2c)
- [GPIO board labelling (article on multiple i2c connections - didn't work on RPi 5)](https://medium.com/@mileperuma/enable-multiple-i2c-ports-on-raspberry-pi-5a8807471737) 

## Two i2c devices simultanously

Attach both of them onto the same pin (however you choose to do that). As long as the devices have different physical addresses (Garmin Lidar-Lite v3: `0x62` and MaxSonar-WR: `0x70`), they will be accessible without issues. This is what it looks like when they are both attached to GPIO2 and GPIO3 (pins 3 and 5) at the same time:

```bash
$ sudo i2cdetect -y 1
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- 62 -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: 70 -- -- -- -- -- -- --
```

