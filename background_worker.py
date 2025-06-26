import threading
import random
import time

class BackgroundWorker:
    thread_event = threading.Event()

    def __init__(self, app, printer_data, socketio):
        self.app = app
        self.printer_data = printer_data
        self.socketio = socketio
    
    def __del__(self):
        self.stop_thread()

    def start_thread(self):
        try:
            self.thread_event.set()  # Activate the event to allow the thread loop to run

            # Create and start the thread
            thread = threading.Thread(target=self.read_data, daemon=True)
            thread.start()

            print("Background task started!")
        except Exception as error:
            return str(error)

    def stop_thread(self):
        """
        Stops the background thread by clearing the event flag.
        """
        try:
            self.thread_event.clear()  # Deactivate the event to stop the thread loop
            print("Background task stopped!")
        except Exception as error:
            return str(error)

    def read_data(self):
        while self.thread_event.is_set():
            try:
                self.printer_data['nozzle_temperature'] = (random.random() * 260)
                self.printer_data['bed_temperature'] = (random.random() * 100)
                self.printer_data['status'] = 'Printing'
                if self.printer_data['print_duration'] < self.printer_data['total_print_time']:
                    self.printer_data['print_duration'] += 1
                else:
                    self.printer_data['status'] = 'Idle'
            except Exception as e:
                self.printer_data['nozzle_temperature'] = f"Error: {e}"
                self.printer_data['bed_temperature'] = f"Error: {e}"
                self.printer_data['status'] = 'Error'
            finally:
                self.socketio.emit('printer_update', self.printer_data)
            self.socketio.sleep(1)