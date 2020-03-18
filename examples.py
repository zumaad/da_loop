from eventloop import EventLoop, ResourceTask, TimedTask


def timed_print():
    """ Will print "hello" every 3 seconds """
    while True:
        print("hello")
        yield TimedTask(3)

def read_from_other_resource():
    txt_file = open('test2.txt')
    yield ResourceTask(txt_file, 'readable')
    data = txt_file.read()
    print(f"data is {data}, performing some transformations and returning it to outer coro")
    return data

def wait_for_other_coroutine():
    """ 
    yield from chains together generators so that when the event loop passes values
    to the outside generator, that value goes to the inner coro. Essentially, the event loop treats
    it as if they are the same coroutine, just that the body if the inner coroutine you are yielding from is
    inside the outer coroutine's body.
    """
    
    print("before other coroutine")
    data = yield from read_from_other_resource()
    print(f"recieved {data} from other inner coro after it did what it had to do with the data")
    
def read_text():
    """ Opens test.txt, yeilds a resource task (tells the event loop that
    it wants to be notified when the the file is readable"""
    txt_file = open('test.txt')
    while True:
        yield ResourceTask(txt_file, 'readable')
        txt_file.seek(0)
        print(txt_file.read())

def writable():
    txt_file = open('test.txt')
    yield ResourceTask(txt_file, 'writable')
    print("it is writable")

def main():
    ev = EventLoop()
    #ev.run_coroutine(timed_print)
    #ev.run_coroutine(read_text)
    #ev.run_coroutine(wait_for_other_coroutine)
    ev.run_coroutine(writable)
    ev.loop()

if __name__ == "__main__":
    main()