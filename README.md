# Reverse engineering Sony PlayMemories Camera Apps #
The latest Sony cameras include an Android subsystem which allows to install apps from the propriatary Sony PlayMemories Camera appstore. This application replicates the functionality of the Sony store and allows you to install custom Android apps on your camera.

**Go to [sony-pmca.appspot.com](https://sony-pmca.appspot.com/) to try it out!**

## Caution! ##
This is an experiment in a very early stage. All information has been found through reverse engineering. It is likely to not work at all or even cause harm to your hardware. If you break your camera, you get to keep both pieces. **We won't take any responsability.**

However, this seems to be safer than tampering with your camera firmware directly.

## Ok ok, can I install Facebook on my camera? ##
I don't know, I haven't tried. Probably not. The apps available in the Sony appstore seem to be specificly built for Sony cameras and contain a considerable amount of "framework" code. The [PMCADemo](https://github.com/ma1co/PMCADemo) project tries to make sense of the Sony APIs.

## How it all works ##
Anyway, here are the juicy technical details:

### Where to begin... ###
If you want to dig into the firmware yourself, here's what to do:

1. Use [nex-hack's fwtool](http://www.nex-hack.info/wiki/development/fwtool) to unpack your favorite camera's firmware (this seems to only work for older firmware versions however)
2. On Windows, use [Explore2fs](http://www.chrysocome.net/explore2fs) to unpack *android_ext2.fsimg* and *android_and_res_ext2.fsimg*
3. *android_ext2.fsimg* contains the interesting apps in the *app* directory

### ScalarAMarket ###
This app is used to download apps directly on your camera via the built-in wifi.
It is basicly a WebKit wrapper which allows you to access the Sony appstore with the special User-Agent header `Mozilla/5.0 (Build/sccamera)`. The requests are redirected to `wifi***.php`. As soon as you decide to download an app, an *xpd* file is loaded which contains the URL to an *spk* file. Using hard coded http authentication, the *spk* file is downloaded.

### ScalarAInstaller ###
An *spk* file is a container for an AES encrypted *apk* file. An RSA encrypted version of the key is contained, too. This app decrypts the *apk* data and hands it to the default android app installer.

### ScalarAUsbDlApp ###
This is the most interesting app, because it handles the communication when installing apps through your computer via USB. On the computer side, things are handled directly in your browser through the PMCA Downloader plugin.

The typical app install process happens as follows:

1. You visit the Sony appstore using the `usb***.php` urls and decide to download an app to your camera.
2. A new task sequence is generated, with a unique identifier, the *correlation id*
3. The plugin downloads an *xpd* file which contains the *portal url* and the 
*correlation id*. The file is sent to the camera. (An *xpd* file is an *ini* file which contains some data and an hmac sha256 checksum.)
4. The camera sends a camera status JSON object (containing serial number, battery level, installed apps, *correlation id*, etc.) to the *portal url* using hard coded authentication. The network data is transmitted via USB. However, everything is SSL encrypted directly in camera. Only https connections with a known root CA are allowed.
5. The server replies with a JSON object containing the next actions to take. This includes the URL of the *spk* package to install, which is again downloaded over https.

### Summary ###
There doesn't seem to be real origin verification in the whole process, only some kind of obfuscation (all necessary keys are hidden somewhere in native libraries included in the market apps). This allows us to replicate the behavior of the Sony appstore which is attempted in this application.

### Why Google appengine? ###
The camera only accepts https connections with certain certificates (see *ScalarAUsbDlApp.apk\assets\CA*). The easiest way i know to get hosting with an accepted SSL certificate is - you guessed it - appengine.

## Thanks to... ##
Without the work done by the people at [nex-hack.info](http://www.nex-hack.info/), this wouldn't have been possible. Thanks a lot!
