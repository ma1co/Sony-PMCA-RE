# Reverse engineering Sony PlayMemories Camera Apps #
The latest Sony cameras include an Android subsystem used to run apps from the proprietary Sony PlayMemories Camera App Store (PMCA). We reverse engineered the installation process. This allows you to install custom Android apps on your camera.

## How to use it? ###
**Go to [sony-pmca.appspot.com](https://sony-pmca.appspot.com/) to try it out!** You can upload your own apps and install them to your camera using the official Sony browser plugin. Since other browser vendors are disabling NPAPI plugins, please try it using **Internet Explorer**.

## Is it safe? ##
This is an experiment in a very early stage. All information has been found through reverse engineering. Even though everything worked fine for our developers, it could cause harm to your hardware. If you break your camera, you get to keep both pieces. **We won't take any responsibility.**

However, this seems to be safer than tampering with your camera firmware directly. We're just interacting with the isolated Android subsystem. Apps you install this way can be uninstalled in the applications manager. In the worst case, a factory reset of the camera clears all data on the Android partitions.

## What about custom apps? ##
You can try your standard Android apps from any app store, they should work more or less, your mileage may vary. Upload your apk file to our website and follow the instructions. Remember that the performance of the cameras is kind of limited. Some of them still run Android 2.3.7. So the Facebook app might not be the best choice.

If you want to develop your custom app, feel free to do so. Debug and release certificates are accepted by the camera. There are a few special Sony APIs which allow you to take advantage of the features of your camera. Have a look at the [PMCADemo](https://github.com/ma1co/PMCADemo) project where we try to make sense of those.

## What about this repository? ##
We replicated the server side of the Sony app store and created a Google appengine [website](https://sony-pmca.appspot.com/) for you to use it. This repository contains the source code.

## How does it all work? ##
Since you asked, here are the juicy technical details:

### Where to begin... ###
If you want to dig into the firmware yourself, here's what to do:

1. Use [nex-hack's fwtool](http://www.personal-view.com/faqs/sony-hack/fwtool) to unpack your favorite camera's firmware (this seems to only work for older firmware versions however)
2. On Windows, use [Explore2fs](http://www.chrysocome.net/explore2fs) to unpack *android_ext2.fsimg* and *android_and_res_ext2.fsimg*
3. *android_ext2.fsimg* contains the interesting apps in the *app* directory

### ScalarAMarket ###
This app is used to download apps directly on your camera via the built-in wifi.
It is basically a WebKit wrapper which allows you to access the Sony app store with the special User-Agent header `Mozilla/5.0 (Build/sccamera)`. The requests are redirected to `wifi***.php`. As soon as you decide to download an app, an *xpd* file is loaded which contains the URL to an *spk* file. Using hard coded http authentication, the *spk* file is downloaded.

### ScalarAInstaller ###
An *spk* file is a container for an AES encrypted *apk* file. An RSA encrypted version of the key is contained, too. This app decrypts the *apk* data and installs it using the package manager.

### ScalarAUsbDlApp ###
This is the most interesting app, because it handles the communication when installing apps through your computer via USB. On the computer side, things are handled directly in your browser through the PMCA Downloader plugin.

The typical app install process happens as follows:

1. You visit the Sony app store using the `usb***.php` urls and decide to download an app to your camera.
2. A new task sequence is generated, with a unique identifier, the *correlation id*
3. The plugin downloads an *xpd* file which contains the *portal url* and the 
*correlation id*. The file is sent to the camera. (An *xpd* file is an *ini* file which contains some data and an hmac sha256 checksum.)
4. The camera sends a camera status JSON object (containing serial number, battery level, installed apps, *correlation id*, etc.) to the *portal url* using hard coded authentication. The network data is transmitted via USB. However, everything is SSL encrypted directly in camera. Only https connections with a known root CA are allowed.
5. The server replies with a JSON object containing the next actions to take. This includes the URL of the *spk* package to install, which is again downloaded over https.

### Summary ###
No origin verification is performed in the whole process. This allows us to replicate the behavior of the Sony app store.

### Why Google appengine? ###
The camera only accepts https connections with certain certificates (see *ScalarAUsbDlApp.apk/assets/CA*). The easiest way I found to get hosting with an accepted SSL certificate is - you guessed it - appengine.

## Special thanks ##
Without the work done by the people at [nex-hack.info](http://www.nex-hack.info/), this wouldn't have been possible. Thanks a lot!
