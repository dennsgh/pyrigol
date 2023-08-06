import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import os
import threading  # import threading module

JSON_FILE = Path(os.getenv("DATA"), "scheduler_state.json")


class Scheduler:

    def __init__(self):
        self.is_running = True
        # Load actions from file, or initialize to empty list if no file exists
        self.actions = self.read_state()

    def start(self):
        while self.is_running:
            self.check_timers()

    def stop(self):
        self.is_running = False

    def check_timers(self):
        now = datetime.now()
        for action in self.actions.copy():
            target_time = datetime.strptime(action['time'], '%Y-%m-%d %H:%M:%S.%f')
            if now >= target_time:
                print(f"Performing scheduled action: {action['action']}")
                action['action'](**action['kwargs'])  # Call the function with the provided kwargs
                action['last_execution'] = str(now)
                # Remove action after execution
                self.actions.remove(action)
        # Save state after every check
        self.write_state()

    def add_action(self, time, action, kwargs):
        self.actions.append({
            'time': str(time),  # 'time' will be a string
            'action': action,
            'kwargs': kwargs,
            'last_execution': None
        })
        # Save state after every new action added
        self.write_state()

    def read_state(self):
        try:
            if JSON_FILE.stat().st_size > 0:
                with open(JSON_FILE, 'r') as f:
                    state = json.load(f)
                    return state
            else:
                return []
        except (FileNotFoundError, ValueError):
            return []

    def write_state(self):
        with open(JSON_FILE, 'w') as f:
            json.dump(self.actions, f, indent=4, default=str)


if __name__ == "__main__":
    # example of using this stand-alone!
    def print_message(msg):
        print(msg)

    scheduler = Scheduler()
    scheduler.add_action(datetime.now() + timedelta(seconds=5), print_message,
                         {'msg': 'Hello, world!'})
    print(scheduler.read_state())
    start_thread = threading.Thread(
        target=scheduler.start)  # Start the scheduler in a separate thread
    start_thread.start()

    time.sleep(6)

    stop_thread = threading.Thread(target=scheduler.stop)  # Stop the scheduler in a separate thread
    stop_thread.start()
