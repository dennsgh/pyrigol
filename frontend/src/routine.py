from pages import factory
import time


def check_connection(args_dict: dict) -> bool:

    if my_generator is not None:
        is_alive = factory.create_dg4202(args_dict)
        if not is_alive:
            factory.last_known_device_uptime = None
            my_generator = None
        # device is alive.
        # transition from dead to alive None -> time
        if factory.last_known_device_uptime is None:
            factory.last_known_device_uptime = time.time()
        return is_alive
    # connection is dead from here
    factory.last_known_device_uptime = None