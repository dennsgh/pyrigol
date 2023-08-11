import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import os
import threading  # import threading module

from typing import Dict, Union


class FunctionMap:
    '''
    Used to statically define functions for the scheduler to use.
    Removes the need to serialize/deserialize certain data (like complex objects)
    '''

    def __init__(self, id: str):
        if not id:
            raise ValueError("A unique name must be provided for the FunctionMap.")
        self.functions = {}
        self.default_kwargs = {}
        self.id = id

    def register(self, name, func, default_kwargs=None):
        """
        Register a new function with a given name and default kwargs.
        """
        if not callable(func):
            raise ValueError(f"{func} is not callable.")
        self.functions[name] = func
        if default_kwargs:
            self.default_kwargs[name] = default_kwargs

    def get(self, name):
        """
        Get the function registered with the given name.
        """
        return self.functions.get(name)

    def get_default_kwargs(self, name):
        """
        Get the default kwargs for a function registered with the given name.
        """
        return self.default_kwargs.get(name)

    def exists(self, name):
        """
        Check if a function is registered with the given name.
        """
        return name in self.functions


class Scheduler:
    '''
    Requires a function map to be usable.
    '''
    default_json = {"actions": [], "last_executed": None}

    def __init__(self, function_map: FunctionMap, interval: float = 0.001, state_file: Path = None):
        self.function_map = function_map
        self.is_running = True
        self.interval = interval
        self.state_file = state_file or Path(os.getenv("DATA", '.'), f"{self.function_map.id}.json")

        data = self.read_state()  # read once
        self.actions = data.get('actions', [])
        self.last_executed = data.get('last_executed')

    def start(self):
        while self.is_running:
            self.check_timers()
            time.sleep(self.interval)

    def stop(self):
        self.is_running = False

    def check_timers(self):
        now = datetime.now()
        window = timedelta(seconds=self.interval * 2)  # Nyquist
        for action in self.actions.copy():
            target_time = datetime.strptime(action['time'], '%Y-%m-%d %H:%M:%S.%f')
            if target_time - window <= now <= target_time + window:
                executed = self.execute_action(action)
                if executed:
                    self.actions.remove(action)  # Remove the executed action from the list
            elif now > target_time + window:
                with open(Path(os.getenv("DATA", '.'), f"{self.function_map.id}.log"), 'a') as f:
                    f.write(
                        f"Skipped past action scheduled for {action['time']} - Action Name: {action['action']}\n"
                    )
                self.actions.remove(action)  # Remove the skipped action from the list
        self.write_state()

    def execute_action(self, action):
        action_name = action['action']
        if self.function_map.exists(action_name):
            function_to_execute = self.function_map.get(action_name)
            default_kwargs = self.function_map.get_default_kwargs(action_name)
            function_to_execute(**default_kwargs)

            self.last_executed = {'action': action_name, 'execution_time': str(datetime.now())}
            self.write_state()
            return True
        else:
            with open(Path(os.getenv("DATA", '.'), f"{self.function_map.id}.log"), 'a') as f:
                f.write(f"Action {action_name} not found in function map.\n")
            return False

    def add_action(self, time, action_name):
        self.actions.append({
            'time': str(time),
            'action': action_name,
            'function_map_id': self.function_map.id
        })
        self.write_state()

    def read_state(self):
        try:
            with open(self.state_file, 'r') as f:
                content = f.read()
                if not content:
                    return self.default_json
                return json.loads(content)
        except (FileNotFoundError, ValueError):
            return self.default_json

    def write_state(self):
        with open(self.state_file, 'w') as f:
            json.dump({
                'actions': self.actions,
                'last_executed': self.last_executed
            },
                      f,
                      indent=4,
                      default=str)


if __name__ == "__main__":
    # example of using this stand-alone!
    def print_hello(**kwargs):
        print(kwargs.get('message', 'Hello World!'))

    def send_email(**kwargs):
        # Mock email sending function
        print(f"Sending email to {kwargs.get('recipient')} with subject {kwargs.get('subject')}")

    function_map = FunctionMap(id="default")
    function_map.register('print_hello', print_hello, default_kwargs={'msg': 'Hello, world 1'})
    function_map.register('send_email', send_email, default_kwargs={'msg': 'Hello, world 1'})

    scheduler = Scheduler(function_map)
    scheduler.add_action(
        time=datetime.now() + timedelta(seconds=5),
        action_name='print_hello',
    )
    scheduler.add_action(
        time=datetime.now() + timedelta(seconds=5),
        action_name='send_email',
    )

    print(scheduler.read_state())
    start_thread = threading.Thread(
        target=scheduler.start)  # Start the scheduler in a separate thread
    start_thread.start()

    time.sleep(6)
    print("Killing timer.")
    stop_thread = threading.Thread(target=scheduler.stop)  # Stop the scheduler in a separate thread
    stop_thread.start()
