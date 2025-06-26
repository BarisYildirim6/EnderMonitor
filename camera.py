# camera.py
import cv2
import threading

class Camera:
    def __init__(self):
        self.capture = cv2.VideoCapture(0)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()

    def _update_frame(self):
        while self.running:
            success, frame = self.capture.read()
            if success:
                with self.lock:
                    self.frame = frame

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            ret, buffer = cv2.imencode('.jpg', self.frame)
            return buffer.tobytes()

    def stop(self):
        self.running = False
        self.thread.join()
        self.capture.release()