#!/usr/bin/env python3

"""

PyTCP, Python TCP/IP stack, version 0.1 - 2020, Sebastian Majewski
stack_tmer.py - module contains class supporting timer that can be used by other stack components

"""

import loguru
import time
import threading


class StackTimerTask:
    """ Timer task support class """

    def __init__(self, method, args, kwargs, delay, delay_exp, repeat_count, stop_condition):
        """ Class constructor, repeat_count = -1 means infinite, delay_exp means to raise delay time exponentialy after each method execution """

        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.delay = delay
        self.delay_exp = delay_exp
        self.repeat_count = repeat_count
        self.stop_condition = stop_condition

        self.remaining_delay = delay
        self.delay_exp_factor = 0

    def tick(self):
        """ Tick input from timer """

        self.remaining_delay -= 1

        if self.stop_condition and self.stop_condition():
            self.remaining_delay = 0
            return

        if self.remaining_delay:
            return

        self.method(*self.args, **self.kwargs)

        if self.repeat_count:
            self.remaining_delay = self.delay * (1 << self.delay_exp_factor) if self.delay_exp else self.delay
            self.delay_exp_factor += 1
            if self.repeat_count > 0:
                self.repeat_count -= 1


class StackTimer:
    """ Support for stack timer """

    def __init__(self):
        """ Class constructor """

        self.logger = loguru.logger.bind(object_name="stack_timer.")

        self.run_stack_timer = True

        self.tasks = []
        self.timers = {}

        threading.Thread(target=self.__thread_timer).start()
        self.logger.debug("Started stack timer")

    def __thread_timer(self):
        """ Thread responsible for executing registered methods on every timer tick """

        while self.run_stack_timer:
            time.sleep(0.001)

            # Tck registered timers
            for name in self.timers:
                self.timers[name] -= 1

            # Cleanup expired timers
            self.timers = {_: __ for _, __ in self.timers.items() if __}

            # Tick registered methods
            for task in self.tasks:
                task.tick()

            # Cleanup expired methods
            self.tasks = [_ for _ in self.tasks if _.remaining_delay]

    def register_method(self, method, args=[], kwargs={}, delay=1, delay_exp=False, repeat_count=-1, stop_condition=None):
        """ Register method to be executed by timer """

        self.tasks.append(StackTimerTask(method, args, kwargs, delay, delay_exp, repeat_count, stop_condition))

    def register_timer(self, name, timeout):
        """ Register delay timer """

        self.timers[name] = timeout

    def timer_expired(self, name):
        """ Check if timer expired """

        self.logger.opt(ansi=True).trace(f"<red>Active timers: {self.timers}</>")

        return not self.timers.get(name, None)
