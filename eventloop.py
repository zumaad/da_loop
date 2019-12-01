from selectors import DefaultSelector
from queue import Queue
from typing import Callable
import heapq


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
    pass

class EventLoop:
    def __init__(self):
        self.task_queue = Queue()

    def register(func: Callable):
        task_queue.put(func)
    
    def loop(self):
        while True:
            try:
                task = self.task_queue.get_nowait()
                next(task)
    