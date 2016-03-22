## App installation ##
This describes how Android apps are installed on Sony cameras.

### Where to begin... ###
If you want to dig into the firmware yourself, here's what to do:

1. Use [fwtool](https://github.com/ma1co/fwtool.py) to unpack your favorite camera's firmware
2. One of the images in the *0700\_part_image* directory contains the Android partition with the interesting apps in the *app* directory

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
4. The camera sends a camera status JSON object (containing serial number, battery level, installed apps, *correlation id*, etc.) to the *portal url* using hard coded authentication. The network data is transmitted via USB. However, everything is SSL encrypted directly in camera. Only https connections signed by a known root CA are allowed. However, the certificate is still accepted if it is expired, revoked and for a different host.
5. The server replies with a JSON object containing the next actions to take. This includes the URL of the *spk* package to install, which is again downloaded over https.

### Summary ###
No origin verification is performed in the whole process. This allows us to replicate the behavior of the Sony app store.
