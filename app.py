#import eventlet
#eventlet.monkey_patch()

import cv2
import io
import time
from camera import Camera
from datetime import datetime, UTC
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, Response
from flask_restful import Resource, Api
from background_worker import BackgroundWorker

app = Flask(__name__)
api = Api(app)
socketio = SocketIO(app, async_mode='threading')

camera = Camera()

# Shared printer data
printer_data = {
    'nozzle_temperature': 'Unknown',
    'bed_temperature': 'Unknown',
    'print_duration': 0,
    'total_print_time': 30,
    'status': 'Idle',
}

worker = BackgroundWorker(app, printer_data, socketio)
worker.start_thread()

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

def gen_frames():
    print("Client connected to /video_feed")
    # Initialize camera (0 = default macOS or USB cam)
    camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        if printer_data['status'] == "Idle":
            eventlet.sleep(1)
        else:
            eventlet.sleep(0.016)
    camera.release()

def gen_frames2():
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    socketio.emit('printer_update', printer_data)
    return render_template('index.html', data=printer_data, time=datetime.now(UTC).timestamp())

@app.route('/logger')
def logger():
    socketio.emit('printer_update', printer_data)
    return render_template('logger.html', data=printer_data)

#@app.route('/video_feed')
#def video_feed():
#    return Response(gen_frames(),
#                    mimetype='multipart/x-mixed-replace; boundary=frame')

class VideoFeed(Resource):
    def get(self):
        return Response(gen_frames2(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.event
def connect():
    print("Client connected")

api.add_resource(VideoFeed, '/video_feed')

if __name__ == '__main__':
    socketio.run(app=app, host='0.0.0.0', port=8081, debug=True, use_reloader=False)
