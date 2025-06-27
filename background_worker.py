import threading
import random
import time

class BackgroundWorker:
    thread_event = threading.Event()

    def __init__(self, app, printer_data, socketio, serial):
        self.app = app
        self.printer_data = printer_data
        self.socketio = socketio
        self.serial = serial
        self.current_progress = 0
        self.total_progress = 100

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

    def test_data(self):
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

    def read_data(self):
        while self.thread_event.is_set():
            try:
                response = self.send_gcode("M105")
                for line in response:
                    print("M105:", line)
                    if "T:" in line and "B:" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            self.printer_data['nozzle_temperature'] = parts[1][2:]
                            self.printer_data['bed_temperature'] = parts[3][2:]
                            self.printer_data['max_nozzle_temperature'] = parts[2][1:-3]
                            self.printer_data['max_bed_temperature'] = parts[4][1:-3]
                        break

                response = self.send_gcode("M27")
                for line in response:
                    print("M27:", line)
                    if "Not SD printing" in line:
                        self.printer_data['status'] = 'Idle'
                        break
                    elif "SD printing byte" in line:
                        self.printer_data['status'] = 'Printing'
                        parts = line.split()
                        if len(parts) >= 4:
                            progress_parts = parts[3].split("/")
                            if len(progress_parts) >= 2:
                                self.current_progress = int(progress_parts[0])
                                self.total_progress = int(progress_parts[1])
                        break
                    elif "No media" in line:
                        self.printer_data['status'] = 'Empty'
                        break

                response = self.send_gcode("M31")
                for line in response:
                    print("M31", line)
                    if "Print time" in line:
                        parts = line.split()
                        hours = 0
                        minutes = 0
                        seconds = 0
                        print_duration = 0
                        if len(parts) >= 5:
                            hours = int(parts[2][:-1])
                            minutes = int(parts[3][:-1])
                            seconds = int(parts[4][:-1])
                        elif len(parts) >= 4:
                            minutes = int(parts[2][:-1])
                            seconds = int(parts[3][:-1])
                        print_duration = (hours * 3600) + (minutes * 60) + seconds
                        total_duration = print_duration / (self.current_progress / self.total_progress)
                        self.printer_data['print_duration'] = print_duration
                        self.printer_data['total_print_time'] = total_duration
                        break
            except Exception as e:
                self.printer_data['nozzle_temperature'] = f"Error: {e}"
                self.printer_data['bed_temperature'] = f"Error: {e}"
                self.printer_data['status'] = 'Error'
                print(e)
            finally:
                self.socketio.emit('printer_update', self.printer_data)
            self.socketio.sleep(1)

    def send_gcode(self, command, wait=0.5, max_lines=5):
        """Send a G-code and wait for valid response lines."""
        self.serial.write((command + "\n").encode('utf-8'))
        time.sleep(wait)

        responses = []
        for _ in range(max_lines):
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    responses.append(line)
                if line == "ok":
                    break
        return responses
