# ipcam-yolo-telegram
I hacked together YOLOv3 and a Telegram bot to notify me via Telegram when a person is detected.

Code comments are... sparse

This is very much WIP and basically is functional enough to work for my needs. I'm quite pleased with the Telegram bot code, although some parts of it *cough*whitelisthandler*cough* could be better...

detect.py does the detection from the camera streams and writes to an output folder. This is heavily derived from the YOLOv3 repo (use my fork to recreate this properly) and the actual detection model is their default you get from running their example notebook. If an object of interest is detected, it is written to the output folder and the Telegram bot monitors this to update users. I still want to do quite a bit of work here, namely:
* have a better understanding of how multiple streams are processed in the inference loop
* remove all the hardwired config and argparsing to a config file
* have a closer look at the OpenCV code used to open the rtsp streams and see if any speed improvements can be had there

To run this, clone the fork of YOLOv3 and then copy these files into it after running the example notebook. I know, suboptimal, but I'm not ready to prune all that code into a single coherent repo

As an aside, I couldn't really find a sane (to me) menthod of handling configs in Python. I'm sure there are better ways that what I've used, but I made a small module called conf_handler, that basically loads and saves a yaml conf from a global variable within itself. I welcome alternative recommendations.
