import eventlet
eventlet.monkey_patch()

import cv2
from datetime import datetime, UTC
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, Response
from background_worker import BackgroundWorker

app = Flask(__name__)
socketio = SocketIO(app)

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

@app.route('/')
def index():
    socketio.emit('printer_update', printer_data)
    return render_template('index.html', data=printer_data, time=datetime.now(UTC).timestamp())

@app.route('/logger')
def logger():
    socketio.emit('printer_update', printer_data)
    return render_template('logger.html', data=printer_data)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.event
def connect():
    print("Client connected")
    
if __name__ == '__main__':
    socketio.run(app=app, host='127.0.0.1', port=8081, debug=False)