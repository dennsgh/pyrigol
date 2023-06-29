# pyrigol

To run the app in WSGI using waitress.

```
python main.py --port 8501 --env production
```

To run the app in dev mode.

```
python main.py --hardware-mock --port 8501 --env development --api-server 5000
```

To setup the environment you might be required to run this:

```
source etc/setup.sh
```

### Options

- `--hardware-mock`: Run the application in hardware mock mode.
- `--debug`: Run the application in debug mode.
- `-p, --port`: Specify the port number to run on. Defaults to 8501.
- `--env`: Specify the environment to run the application in. Defaults to development. Available choices are 'development' and 'production'.

Example usage:

```shell
python main.py --hardware-mock --port 8501 --env production
```

# Rigol DG4202 USB Driver Setup

## Prerequisites

Before connecting your Rigol DG4202 device to your computer via USB, you need to install the necessary drivers and software. These drivers enable your operating system to recognize the device and allow applications to interact with it.

## Step-by-Step Installation

1. **Install NI-VISA Driver**: The National Instruments Virtual Instrument Software Architecture (NI-VISA) is a software API that greatly simplifies configuration and programming of your Rigol DG4202. [Download the NI-VISA driver](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) and follow the installation instructions. Please note that you need to reboot your computer after installing NI-VISA.

2. **Install Rigol USB Driver**: This is the specific driver for Rigol devices. You can [download the Rigol USB driver](https://rigolshop.eu/products/waveform-generators-dg4000-dg4202.html) from the official Rigol website. After downloading, unzip the file and follow the included instructions to install the driver.

## Verifying Installation

After installing the drivers, connect your Rigol DG4202 to your computer using a USB cable. Power on the device and check if your operating system recognizes the device correctly.

You can check this by using the `pyvisa` library in Python:

```python
import pyvisa

rm = pyvisa.ResourceManager()
print(rm.list_resources())
```
