# Reverse engineering Sony PlayMemories Camera Apps #
The latest Sony cameras include an Android subsystem used to run apps from the proprietary Sony PlayMemories Camera App Store (PMCA). We reverse engineered the installation process. This allows you to install custom Android apps on your camera.

## How to use it? ###
There are two ways to install apps on your camera. Be sure it is connected over USB and set to MTP or mass storage mode.

### Browser plugin ###
**Go to [sony-pmca.appspot.com](https://sony-pmca.appspot.com/) to try it out!** You can upload your own apps and install them to your camera using the official Sony browser plugin. Since other browser vendors are disabling NPAPI plugins, please try it using **Internet Explorer**.

### Local installer ###
Download the [latest release](https://github.com/ma1co/Sony-PMCA-RE/releases/latest) (Windows or OS X) or clone this repository. Run `pmca --help` for more information.

#### Usage ####
* Test the USB connection to your camera (the result is written to the specified file):

        pmca install -o outfile.txt

* Install an app on your camera (the app is uploaded and served from Google appengine):

        pmca install -f app.apk

* Install an app using a local web server:

        pmca install -s "" -f app.apk

* Download apps from the official Sony app store (interactive):

        pmca market

#### Windows drivers ####
On Windows, the choice defaults to the default Windows USB drivers. If you want to use libusb on Windows, you'll have to install generic drivers for your camera using [Zadig](http://zadig.akeo.ie/) (select *libusb-win32*). You can then run `pmca install -d libusb`.

## Is it safe? ##
This is an experiment in a very early stage. All information has been found through reverse engineering. Even though everything worked fine for our developers, it could cause harm to your hardware. If you break your camera, you get to keep both pieces. **We won't take any responsibility.**

However, this seems to be safer than tampering with your camera firmware directly. We're just interacting with the isolated Android subsystem. Apps you install this way can be uninstalled in the applications manager. In the worst case, a factory reset of the camera clears all data on the Android partitions.

## What about custom apps? ##
You can try your standard Android apps from any app store, they should work more or less, your mileage may vary. Upload your apk file to our website and follow the instructions. Remember that the performance of the cameras is kind of limited. Some of them still run Android 2.3.7. So the Facebook app might not be the best choice.

If you want to develop your custom app, feel free to do so. Debug and release certificates are accepted by the camera. There are a few special Sony APIs which allow you to take advantage of the features of your camera. Have a look at the [PMCADemo](https://github.com/ma1co/PMCADemo) project where we try to make sense of those.

## About this repository ##
* **pmca.py**: Source for the USB installer console application. See the releases page for pyinstaller builds for Windows and OS X.
* **main.py**: The source code for the Google App Engine website served at [sony-pmca.appspot.com](https://sony-pmca.appspot.com/).
* **docs**: Technical documentation

## Special thanks ##
Without the work done by the people at [nex-hack](http://www.personal-view.com/faqs/sony-hack/hack-development), this wouldn't have been possible. Thanks a lot!
