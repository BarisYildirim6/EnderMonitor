import picamera2
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import libcamera
import io

import subprocess
from threading import Condition
import time
import os

class Camera:
    def __init__(self):
        self.camera = picamera2.Picamera2()
        self.camera.configure(self.camera.create_video_configuration(main={"size": (640, 480)}, transform=libcamera.Transform(hflip=0, vflip=1)))
        self.still_config = self.camera.create_still_configuration()
        self.encoder = MJPEGEncoder(10000000)
        self.streamOut = StreamingOutput()
        self.streamOut2 = FileOutput(self.streamOut)
        self.encoder.output = [self.streamOut2]

        self.camera.start_encoder(self.encoder)

    def get_frame(self):
        self.camera.start()
        with self.streamOut.condition:
            self.streamOut.condition.wait()
            self.frame = self.streamOut.frame
        return self.frame

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
