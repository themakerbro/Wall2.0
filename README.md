# Wall2.0
Starting with a clean install of Raspbian Jessie.
```
sudo apt-get install bluez libusb-dev pyqt4-dev-tools joystick libbluetooth-dev libjack0 libjack-dev
sudo hciconfig hci0 up
```
### Connect controller via USB
```
sudo ./sixpair
```
### Disconnect controller from USB
git clone https://github.com/falkTX/qtsixa/ (if needed)
make
make install
