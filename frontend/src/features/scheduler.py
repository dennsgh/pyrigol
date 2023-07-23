import time
import json
from datetime import datetime
from pathlib import Path
import os

JSON_FILE = Path(os.getenv("DATA"), "scheduler_state.json")


class Scheduler:

    def __init__(self):
        self.ticks = 0
        self.is_running = True
        # Load actions from file, or initialize to empty list if no file exists
        self.actions = self.read_state()

    def start(self):
        while self.is_running:
            t0 = time.perf_counter()
            self.check_timers()
            t1 = time.perf_counter()
            elapsed = t1 - t0
            remaining = max(1 - elapsed,
                            0)  # Calculate remaining time for sleep, ensuring it's not negative
            time.sleep(remaining)  # Sleep for the remaining time

    def stop(self):
        self.is_running = False

    def check_timers(self):
        self.ticks += 1
        print(f"Tick: {self.ticks}")
        for action in self.actions:
            if self.ticks % action['time'] == 0:
                print(f"Performing scheduled action: {action['action'].__name__}")
                action['action'](**action['kwargs'])  # Call the function with the provided kwargs
                action['last_execution'] = str(datetime.now())
        # Save state after every check
        self.write_state()

    def add_action(self, time, action, kwargs):
        self.actions.append({
            'time': time,
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
    scheduler.add_action(5, print_message, {'msg': 'Hello, world!'})
    scheduler.start()
