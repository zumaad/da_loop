An event loop exists to notify you when a resource that you want to be readable/writable is actually readable/writable. This is an alternative to the multi threaded approach where you can handle each resource you want to monitor its own thread and constantly poll it/block the thread until its readable/writable.

The following is an example of when an event loop can be useful:

You are building a server which can talk with many clients at the "same" time. The way the clients
and server communicate is through sockets. A client can open a TCP socket, connect to the server, and the server gets a corresponding socket that it can communicate with that specific client with when it accepts that client's connection.

Now, lets say that 10 different clients initiate a connection with the server. The Server now has 10 different socket objects that it can send data to and read data from, to communicate with the 10 different clients.

The clients can send data at any time, or they could send no data at all! And when sending data back to clients, they may not be able to accept the data (their socket buffer is full). This introduces some complexity :(

To communicate with all these clients, you can generally take two approaches:

1. Use multithreading. For example, you could create 10 new threads and in those threads you could be waiting for data from the client and then responding appropriately. This approach allows you to wait indefinetely until a client sends data/until you can send data to the client without preventing you from servicing other clients because every client is handled in its own thread.

2. Use non blocking sockets, check if a socket has data in it/you can send data to it, respond appropriately and move onto the next socket and loop. You typically don't do this manually as you usually use the select system call which returns you readable/writable sockets. In python for example, you can use the "selectors" library and register your sockets with a selector. Then you can do something like selector.select() which will return you the readable/writable sockets. So the flow would be: call selector.select(), get a list of readable/writable sockets, if its readable then read the data and respond appropriately, if its writable then write data to it, loop. If a socket becomes unwritable/unreadable as you are reading/writing to it, you just stick it back in the selector and associate a function with it (a callback) so that when you see it again you can service it according to where you left off. This is basically an event loop! Just a really primitive one.

what you CAN'T DO is use blocking sockets in a single threaded context and try to read data from each one because the socket may not have data in it (client didn't send anything) and with blocking sockets if there isn't data, it will wait for data, thus blocking the thread and preventing you from servicing other clients! Non blocking sockets will work because if there is no data in the socket, a call to read from the socket (socket.recv) won't wait for data, it will immediately return with data (if there is any) or throw an exception if there isn't, thus allowing you to move on to clients without waiting on a client.

Approach #1 works, but threads have additional overhead and multithreaded programming can be incredibly
difficult to debug.

Approach #2 (very primitive event loop) works, but it can make your code very unreadable quickly. For example, lets say that your server isn't only interacting with the client and sending back some data. Lets say that when the server gets data from a client, it opens a connection to another server (server2), sends the data the client sent and awaits a response, and then forwards that data back to the client and maybe even does some additional processing with some other function calls. What happens when server2 takes a long time to send back data, or currently can't accept data or for whatever reason can't respond immediately? Well, you have its socket so you can just monitor its socket like you are monitoring the clients' sockets to see if its readable/writable instead of waiting. This works! But..it makes things messy. Here is why

Lets say this is the order of operations to service a client.

1. read data from client
2. open conn to server2
3. send client data to server2
4. read data from server2
5. process data
6. send back data to client

The following operation numbers are where you can potentially be forced to abandon this process due to the client/server2 sockets not being writable/readable: 1,2,3,4,6. Lets say you try to send client data to server 2 (operation 3) and its socket throws an error because its currently not writable. Thats fine, you just stick it back in the selector and associate it with a callback so that when you see it again (when its writable) you can use that function to start sending data back to server2! Wait....what will that function look like?? The function will have to finish sending the data to server2(operation 3) and then do operation 4, 5, and 6 to finish servicing the client. BUT WAIT, what if that function has to be abandoned at step 4 because server2 didn't immediately send back data? you would have to associate another callback with it that finishes step 4, 5 and 6. Imagine if the code is even more complicated with more intermediate connections/servers being talked to. The callbacks you would have to associate with a socket would be horribly complicated, nested and just overall unreadable. That's callback hell. We don't want that. So we need some way to be able to use this event loop architecture while still programming in a simple top down manner like the order of operations above looks like.

There are different ways to handle this, different languages might have different constructs that lead to different implementations. The way my event loop handles this is through the use of generators in Python.

A generator is essentially a function that behaves like an iterator. It doesn't run all at once, it runs until it hits a "yield statement" (which can return a value to the caller) and you have to call next() on it again to make it progress further and so on.

For example:

def gooby():
    print("hi")
    yield 10
    print("after first yield")
    yield
    print("print after second yield")

gen = gooby() #this creates the generator object
val = next(gen) #this will print "hi" and val will = 10
next(gen) #this will print "after first yield"
next(gen) #this will print "after second yield"

This is incredibly important because it essentially allows us to "pause" the execution of a function and come back to the place we left off when we need to. This solves the problem we had on callback hell!
Lets take a look at the list of operations to service a client again.


1. read data from client
2. open conn to server2
3. send client data to server2
4. read data from server2
5. process data
6. send back data to client


remember the following operation numbers are where you can potentially be forced to abandon this process due to the client/server2 sockets not being writable/readable: 1,2,3,4,6.


imagine if before trying to do those troublesome operations we could ask the eventloop if the socket was readable/writable and only move forward in the generator if it was. We can ask the event loop this by yielding the resource which the event loop will get as its calling next() on the generator. Then when the event loop sees the socket is readable/writable (using the select system call) it 
calls next() on the generator which moves it forward and actually does the reading/writing operation. For example

def service_client(client_socket):
    yield client_socket
    data = client_socket.read()

    server2_socket = socket.connect(server2_address)

    yield server2_socket
    server2_socket.send(data)

    yield server2_socket
    response = server2_socket.read()

    yield client_socket
    client_socket.send(response)

So lets say you have the function/generator above and you tell the event loop to run it. The event loop 
starts running it, calls next() on it, gets the client socket and adds it to its selector. Then it calls selector.select() and the client socket is still unreadable, so the event loop loops again and calls selector.select() and this time the client socket is readable, so it calls next() on the service_client generator which then executes client_socket.read() and stops at the yield server2_socket line. So essentially, you pause the function until the resource it requests is readable/writable. This can be achived quite easily by having some sort of mapping between a yielded resource/socket and the generator that yielded it. That way the event loop is essentially a while true loop that keeps track of all the readable/writable sockets and a mapping of yielded socket/resource to the generator that yielded it. It can then iterate through the mapping, see whether the yielded socket is in the collection of readable/wrtiable sockets, and if it is, call next() on the associated generator and so on. 


