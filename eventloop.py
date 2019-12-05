from selectors import DefaultSelector
from queue import Queue
from typing import Callable
import heapq
import datetime


class PriorityQueue:
    def __init__(self):
        self.heap = []
    
    def put(self):
        pass

    def pop(self):
        pass

class Task:
    pass

class TimedTask:
    def __init__(self, delay):
        self.delay = delay
        self.delay_time = datetime.timedelta(seconds=delay)
        self.start_time = datetime.datetime.now()
        self.end_time = self.start_time + self.delay_time
    
    def is_complete(self) -> bool:
        return datetime.datetime.now() > self.end_time
    
    def __str__(self):
        return str(vars(self))

class EventLoop:
    def __init__(self):
        self.task_queue = Queue()
        self.coroutines = []
        self.task_to_coroutine = {}

    def register(self, func: Callable):
        coroutine = func()
        # coroutine.send(None)
        self.coroutines.append(coroutine)
    
    def loop(self):
        for coroutine in self.coroutines:
            task = next(coroutine)
            self.task_to_coroutine[task] = coroutine
        
        while True:
            for task, coroutine in list(self.task_to_coroutine.items()):
                if task.is_complete():
                    new_task = next(coroutine)
                    if new_task:
                        self.task_to_coroutine[new_task] = coroutine
                    del self.task_to_coroutine[task]
                        
def coro1():
    while True:
        print("hello")
        yield TimedTask(5)

def coro2():
    while True:
        print("bye")
        yield TimedTask(1)


if __name__ == "__main__":
    event_loop = EventLoop()
    event_loop.register(coro1)
    event_loop.register(coro2)
    event_loop.loop()