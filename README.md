# Reverse Engineering Sony Digital Cameras
This tool interfaces with Sony digital cameras through USB. It allows to tweak settings, dump firmware, and in some cases install custom Android apps.

## Installation
There are two binaries:

* **pmca-console**: The main command line application
* **pmca-gui**: A graphical user interface with a limited set of features

### Windows
The application should work fine on Windows using the operating system's mass storage and MTP USB drivers.

Download the [latest stable release](https://github.com/ma1co/Sony-PMCA-RE/releases/latest) or the newest [development build](https://ci.appveyor.com/project/ma1co/sony-pmca-re/build/artifacts).

### macOS
macOS binaries are also distributed, but less tested than the Windows equivalents. Getting the USB drivers to work may require some fiddling. To communicate with cameras in mass storage mode, Sony's [Camera Driver](https://support.d-imaging.sony.co.jp/mac/driver/11/ja/) has to be installed. Make sure to close all applications which could access USB drivers, including Photos, Dropbox and Google Drive.

The latest release binaries can be found in the [release section](https://github.com/ma1co/Sony-PMCA-RE/releases/latest).

### Linux
The application uses Python 3 and should work fine on Linux using libusb drivers.

Clone or download this repository, then run the following commands:
```bash
pip install -r requirements.txt  # to install the dependencies
./pmca-console.py  # for the command line application
./pmca-gui.py  # for the gui application
```

## Usage
There are three main modes of interfacing with a camera:

### App Installer
If the camera supports *PlayMemories Camera Apps (PMCA)*, it is possible to install custom Android apps using this tool. A list of supported cameras can be found [here](https://openmemories.readthedocs.io/devices.html).

It is recommended to install the [*OpenMemories: Tweak*](https://github.com/ma1co/OpenMemories-Tweak) app. This app allows to tweak settings and to start *telnet* and *adb* servers to execute code on the system.

Other apps are available. A list can be found [here](https://github.com/ma1co/OpenMemories-AppList).

There are two ways to install apps:
* **pmca-gui**: In the *Install app* tab, select an app from the list and click *Install selected app*.
* **pmca-console**: Run `pmca-console install -i` to interactively select an app to install.

### Firmware Updater
Sony cameras can boot from a secondary partition for firmware updates. Using a custom firmware file, we can execute code in this mode. Note that the camera firmware itself remains untouched. The firmware update process is only used to execute custom code.

This mode does not require any special drivers, the operating system's mass storage USB driver is enough.

A list of supported camera models can be found [here](https://openmemories.readthedocs.io/devices.html). Devices based on the CXD90045 and CXD90057 architectures are not compatible, since their firmware is cryptographically signed.

There are two ways to use this:
* **pmca-gui**: In the *Tweaks* tab, click *Start tweaking (updater mode)*. You can then use the checkboxes to configure your camera's settings.
* **pmca-console**: Run `pmca-console updatershell`. There are commands available to dump the firmware, execute Linux commands, and to tweak settings.

Note that this requires rebooting the camera to firmware update mode. You will be guided through this process.

### Service Mode
Sony cameras have a USB mode called *senser mode*, which is used during servicing for calibration and other things. It can also be used to execute code on the running system.

Service mode has the best camera compatibility, but requires custom USB drivers.

It is currently only supported in the command line application:
* **pmca-console**: Run `pmca-console serviceshell`. There are commands available to dump the firmware and to execute Linux commands.

#### Windows Drivers
To use service mode on Windows, custom drivers have to be installed using [Zadig](http://zadig.akeo.ie/):
* Make sure the camera is connected in mass storage mode.
* In Zadig, check *Options -> List All Devices*, select the camera, select *libusb-win32* and click *Replace Driver*.
* Run `pmca-console serviceshell` to make the camera switch modes.
* Once the camera has switched, repeat the above step to install a driver for service mode.
* You should now be able to use `pmca-console serviceshell`.

To be able to use the camera normally again, the libusb drivers have to be uninstalled in device manager.

## Is it safe?
This is an experiment in a very early stage. All information has been found through reverse engineering. Even though everything worked fine for our developers, it could cause harm to your hardware. If you break your camera, you get to keep both pieces. **We won't take any responsibility.**

## What about custom apps?
It is possible to develop custom Android apps for supported cameras. Keep in mind that they should be compatible with Android 2.3.7. Debug and release certificates are accepted by the camera. See [*PMCADemo*](https://github.com/ma1co/PMCADemo) for a demo app.

There are a few special Sony APIs which allow you to take advantage of the features of your camera. They can be used through [*OpenMemories: Framework*](https://github.com/ma1co/OpenMemories-Framework).

## Special thanks
Without the work done by the people at [nex-hack](http://www.personal-view.com/faqs/sony-hack/hack-development), this wouldn't have been possible. Thanks a lot!
