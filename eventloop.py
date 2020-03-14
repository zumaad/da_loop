import selectors
from queue import Queue
from typing import Callable
import heapq
import datetime
import socket

class ResourceTask:
    """ 
    A resource task is a task that is dependent on a file like object (socket or actual file for example) to 
    be readable or writable. A coroutine will yield this type of task so that it can be resumed by the event loop when
    the file like object is readable or writable. For example, lets say that you have a coroutine that is making a server request
    and needs to wait for the response
    The server could take a long time to send the response, and you want to be able to do other things during that time. So, the
    function just has to yield event_loop.resource_task(socket_that_communicates_with_server, 'readable'). The coroutine will then be paused
    and the event loop will run other coroutines. When the event loop notices that the 'socket_that_communicates_with_server' is 
    readable (meaning it has data in it), then the couroutine associated with the task will be resumed. 

    This ResourceTask class is never called explicitly by the coroutines, the coroutines use the 'resource_task' method on the 
    EventLoop class to create a ResourceTask which they then yield.
    """
    EVENT_TO_SELECTORS_EVENT = {
        #selectors.EVENT_WRITE and EVENT_READ are just ints, but its better to use the variable names.
        'writable':selectors.EVENT_WRITE,
        'readable':selectors.EVENT_READ 
    }

    def __init__(self, resource, event: str, event_loop):
        """
        a event such as writable or readable along with a resource such as a socket or a file is provided. The resource is registered
        with the event loop so that the event loop can store it in a Selector which it uses to monitor which resources are ready to give back
        to the coroutine that yielded them.
        """
        self.event_loop = event_loop
        self.resource = resource
        try:
            event_to_wait_for = self.EVENT_TO_SELECTORS_EVENT[event]
            self.event_loop.register_resource(resource, event_to_wait_for)
        except KeyError:
            raise KeyError(f"you did not provide a valid event associated with this resource task. Valid events are {self.EVENT_TO_SELECTORS_EVENT}")

    def is_complete(self) -> bool:
        """ 
        Checks whether the resource associated with this task, like a socket, is readable (has data in it that someone else sent) 
        or writeable (can recieve data). 
        """
        return self.resource in self.event_loop.ready_resources
    
    def get_new_task(self, coroutine):
        """
        After a task is completed, the coroutine is resumed by calling next(coroutine). Coroutines that yield ResourceTasks 
        have two yield statements. Lets take the following coroutine as an example:

        def gooby():
            yield event_loop.resource_task(some_socket, 'readable') #point 1
            print("after the first yield statement) #point 2
            socket_with_data_in_it = yield #point 3
            print(f"the socket has the following data in it: {socket_with_data_in_it.recv(1000)})
        
        the coroutine will be run, and the resource task will be yielded (point 1). Then, during the event loop's looping to check whether tasks
        are complete, the resource task will have completed and the coroutine will be run again and it will pass point 1 and 2 to get to point 3 where it will 
        stop again. Thats when the coroutine will be sent the resource it requested. The empty yield in point 3 is used to accept a value passed
        IN to a generator from outside.  

        """
        next(coroutine) #get past the first yield
        try:
            self.event_loop.resource_selector.unregister(self.resource) #stop monitoring resource as the event has already happened
            new_task = coroutine.send(self.resource) #send the resource back to the coroutine that yielded the ResourceTask
            return new_task
        except StopIteration: #the coroutine dies if there are no more yields
            return None

    def __str__(self):
        return str(vars(self))
    
    
class TimedTask:
    """
    A TimedTask is simply used to pause a coroutine for the given delay. The coroutine that 
    yielded the TimedTask will be resumed after the timedtask is complete.
    """
    def __init__(self, delay: int):
        self.delay = delay
        self.delay_time = datetime.timedelta(seconds=delay)
        self.start_time = datetime.datetime.now()
        self.end_time = self.start_time + self.delay_time
    
    def is_complete(self) -> bool:
        return datetime.datetime.now() > self.end_time
    
    def get_new_task(self, coroutine):
        try:
            new_task = next(coroutine)
            return new_task
        except StopIteration:
            return None
    
    def __str__(self):
        return str(vars(self))

class EventLoop:
    """
    The great event loop. This class is responsible for running coroutines, getting tasks from them, checking whether the tasks
    are complete, and then resuming the coroutines and passing in any resources the coroutines may need.
    """

    def __init__(self):
        self.task_to_coroutine = {}
        self.ready_resources = set()
        self.resource_selector = selectors.DefaultSelector()
        
    def register_resource(self, resource, event: int):
        self.resource_selector.register(resource, event)

    def run_coroutine(self, func: Callable, *func_args):
        coroutine = func(*func_args)
        task = next(coroutine)
        if task:
            self.task_to_coroutine[task] = coroutine
        
    def resource_task(self, resource, event: str) -> ResourceTask:
        return ResourceTask(resource, event, self)

    def timed_task(self, delay: int) -> TimedTask:
        return TimedTask(delay)

    def loop(self):
        """
        This is the meat of the event loop. 
        """
        self.ready_resources = set(self.resource_selector.select(-1))
        while True:
            for task, coroutine in list(self.task_to_coroutine.items()):
                new_task = None
                if task.is_complete():
                    new_task = task.get_new_task(coroutine)
                    del self.task_to_coroutine[task]

                    if new_task:
                        self.task_to_coroutine[new_task] = coroutine

            self.ready_resources = set(resource_wrapper.fileobj for resource_wrapper, event in self.resource_selector.select(-1))

def read_text(ev):
    txt_file = open('test.txt')
    while True:
        print("yielding resource")
        yield ev.resource_task(txt_file, 'readable')
        print("after yielding resource")
        file_with_data = yield #point 3
        print(file_with_data.read())



def main():
    ev = EventLoop()
    ev.run_coroutine(read_text, ev)
    ev.loop()

if __name__ == "__main__":
    main()

