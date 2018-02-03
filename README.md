# Reverse engineering Sony PlayMemories Camera Apps #
The latest Sony cameras include an Android subsystem used to run apps from the proprietary Sony PlayMemories Camera App Store (PMCA). The tools provided in this repository allow you to install custom Android apps on your camera.

Additional effort has been made to analyze the firmware update process. Using the obtained knowledge, we can execute custom code on almost all Sony Cybershot and Alpha cameras released between 2007 and 2016.

## Installing Android apps ##
The list of cameras featuring the Android subsystem can be found [here](https://github.com/ma1co/OpenMemories-Framework/blob/master/docs/Cameras.md).

The list of available apps can be found at [sony-pmca.appspot.com](https://sony-pmca.appspot.com/). If you are using Internet Explorer or Safari, apps can be installed directly from your browser. Other browsers and recent camera firmware updates are not compatible with this method anymore. It is recommended to use the native installers (pmca-gui and pmca-console) instead.

**pmca-gui is the recommended way to install apps.** Binaries for Windows and OS X are available in the [release section](https://github.com/ma1co/Sony-PMCA-RE/releases/latest). Download and open the program, connect your camera via USB, go to the *Install* tab, select an app from the list and click *Install*.

Further information can be found in the sections below.

## Tweaking camera settings ##
If your camera supports Android apps, we suggest using [OpenMemories: Tweak](https://github.com/ma1co/OpenMemories-Tweak). Otherwise, the tweaks can be applied using a method based on the firmware update process: In pmca-gui, go to the *Tweaks* tab and click the *Start tweaking* button. Follow the directions on your camera screen to reboot to firmware update mode. You can now use the checkboxes to configure your camera's settings. Click *Done* to reboot back to normal mode.

This process will only change settings on your camera. The firmware itself remains untouched. The firmware update process is only used to execute custom code.

The list of supported camera models can be found [here](https://github.com/ma1co/fwtool.py/blob/master/devices.yml). Many more models should be compatible, however. If your camera is not listed but you think it should be, please open an issue.

## Further information ##
### Browser plugin ###
The browser-based installer can be found at [sony-pmca.appspot.com](https://sony-pmca.appspot.com/). This site uses the official Sony browser plugin to communicate with the camera directly from a browser window. Since other browser vendors are disabling NPAPI plugins, this method only works in Internet Explorer and Safari. Additionally, camera firmware updates released in June 2017 and later explicitly whitelist the URL of the official app store. Updated cameras refuse to install apps from our site. It is thus recommended to use the native installer instead.

Meanwhile, the site is still used to keep track of the installation counters for the apps in the app list.

### Native installer ###
The native installer directly communicates with cameras over USB (MTP and mass storage connections are supported; for OS X see the notes below). All camera firmware versions are supported.

This installer can also be used by developers to install .apk files from their computer.

Download the [latest release](https://github.com/ma1co/Sony-PMCA-RE/releases/latest) (Windows or OS X) or clone this repository.

#### Graphical user interface ####
Run `pmca-gui` for a simple gui.

#### Command line ####
Run `pmca-console` in the command line for more options. Usage:

* Test the USB connection to your camera (the result is written to the specified file):

        pmca-console install -o outfile.txt

* Install an app from the app list:

        pmca-console install -i

* Install an app on your camera (the app is served from a local web server):

        pmca-console install -f app.apk

* Download apps from the official Sony app store (interactive):

        pmca-console market

* Update the camera's firmware:

        pmca-console firmware -f FirmwareData.dat

* Switch to firmware update mode and run an interactive shell:

        pmca-console updatershell

* Update the GPS assist data:

        pmca-console gps

#### Windows drivers ####
On Windows, the choice defaults to the default Windows USB drivers. If you want to use libusb on Windows, you'll have to install generic drivers for your camera using [Zadig](http://zadig.akeo.ie/) (select *libusb-win32*). You can then run `pmca-console install -d libusb`.

#### OS X drivers ####
On OS X, to communicate with cameras in mass storage mode, the [PMCADownloader](https://sony-pmca.appspot.com/plugin/install) browser plugin and/or the [DriverLoader](https://support.d-imaging.sony.co.jp/mac/driver/1013/en/) application have to be installed.

## Is it safe? ##
This is an experiment in a very early stage. All information has been found through reverse engineering. Even though everything worked fine for our developers, it could cause harm to your hardware. If you break your camera, you get to keep both pieces. **We won't take any responsibility.**

However, this seems to be safer than tampering with your camera firmware directly. We're just interacting with the isolated Android subsystem. Apps you install this way can be uninstalled in the applications manager. In the worst case, a factory reset of the camera clears all data on the Android partitions.

## What about custom apps? ##
You can try your standard Android apps from any app store, they should work more or less, your mileage may vary. Upload your apk file to our website and follow the instructions. Remember that the performance of the cameras is kind of limited. Some of them still run Android 2.3.7. So the Facebook app might not be the best choice.

If you want to develop your custom app, feel free to do so. Debug and release certificates are accepted by the camera. There are a few special Sony APIs which allow you to take advantage of the features of your camera. Have a look at the [PMCADemo](https://github.com/ma1co/PMCADemo) project where we try to make sense of those.

## About this repository ##
* **pmca-console.py**: Source for the USB installer console application. See the releases page for pyinstaller builds for Windows and OS X.
* **pmca-gui.py**: A simple gui for pmca-console. See the releases page.
* **main.py**: The source code for the Google App Engine website served at [sony-pmca.appspot.com](https://sony-pmca.appspot.com/).
* **docs**: Technical documentation

## Special thanks ##
Without the work done by the people at [nex-hack](http://www.personal-view.com/faqs/sony-hack/hack-development), this wouldn't have been possible. Thanks a lot!
