Title: Understanding CSP channels and buffers
Category: JavaScript
Date: 2015-04-04

In a previous post I wrote an [introduction to CSP in JavaScript](/introduction-to-communicating-sequential-processes-in-javascript.html),
where we learned that channels in CSP serve two purposes: conveyance of values and synchronization. I mentioned that several
synchronization semantics can be achieved through the use of buffers but we didn't go into detail about that. This post will explore
channel internals and the synchronization strategies through buffers in CSP usign the [js-csp](https://github.com/ubolonton/js-csp) library.

## Channel internals

In this section we'll understand the internals of a CSP channel as found in [core.async](https://github.com/clojure/core.async) or `js-csp` libraries, and learn about their method
of operation. This information will help us understand buffering better and make more informed decissions about the buffering strategies
we choose.

A channel is an queue-like object where three operations can be performed: put, take and close. Only one value at a time can be put or taken.
Internally, a channel encapsulates:

- A boolean flag (`closed`) that indicates whether is closed or not.
- A buffer where the data that is "put" will be stored waiting to be delivered to the takers.
- Two queues for storing the pending put and take operations.
- A transducer for transforming the values that are put into the channel.

There are also some invariants that a channel must preserve, namely:

- There shouldn't be both pending puts and takes at the same time.
- If the buffer contains any data, a take shouldn't be queued in the pending queue.
- If there is room in the buffer, a put shouldn't be queued in the pending queue.

We will forget about the transducer part for now since I will write about that in an upcoming post. Let's learn about how channels work under
the hood when doing puts and takes.

### put

When performing a put operation in a channel, we can encounter the channel in one of these three states:

1. There are pending takes (hence no pending puts nor data in the buffer).
2. There is room in the buffer (hence no pending puts nor pending takes).
3. There isn't room in the buffer (hence no pending takes but possibly pending puts).

For each of those states the channel will behave differently, preserving the invariants outlined above.

1. If there are pending takes, the put operation will complete immediately and the value will be delivered to the
   first pending taker.
2. If there is room in the buffer, the put operation will also complete immediately and the value will be added to
   the buffer.
3. If there isn't room in the buffer, the put operation will be queued in the queue of pending puts.

The third case is the only one in which the put operation "blocks" because it can't be performed immediately.

### take

When performing a take operation in a channel, we can encounter the channel in one of three states analogous to those
we described earlier for put operations:

1. There are pending puts (hence no pending takes and a full buffer).
2. There are no pending puts but there is data in the buffer (hence no pending takes).
3. There are pending takes (hence no pending puts and an empty buffer).

As with puts, for each of those states the channel will behave differently, preserving its invariants.

1. If the buffer is full, the take operation will complete immediately taking the first value of the buffer. This will
   cause a pending put (if any) to complete putting its value in the buffer.

2. If there is data in the buffer but no pending puts, the take operation will complete immediately taking the first value
   of the buffer.

3. If there isn't any data in the buffer, the take operation will be queued in the queue of pending takes.

## Buffers

As I mentioned in the previous post, buffers synchronize put and take operations inside a channel. When creating a channel with `js-csp`'s `chan`
constructor and not providing a buffer, the channel will be unbuffered. This means that put operations won't succeed until
a take operation comes in and viceversa.

Here is an example of synchronization with a unbuffered channel:

```javascript
import {chan, take, put, go, timeout} from "js-csp";

let unbufferedChan = chan();

go(function*(){
    yield put(unbufferedChan, 42);
    console.log("put completed!");
    yield put(unbufferedChan, 42);
    console.log("put completed!");
});

go(function*(){
    console.log("waiting a second");
    yield timeout(1000);
    yield unbufferedChan;
    console.log("take completed!");
});

//=> "waiting a second"
//=> "take completed!"
//=> "put completed!"
```

As we can see from the logged sentences, a put and a take must rendezvous for them to complete.

### Fixed

The `chan` constructor accepts passing in either a number or a buffer. When we give it a number, a
fixed buffer of that size will be created. This two calls are equivalent:

```javascript
import {chan, buffers} from "js-csp";

chan(1);
chan(buffers.fixed(1))
```

Having a fixed buffer means that, while there is room in the buffer, the put operations will succeed. Let's see
an example of how a fixed buffer behaves with an example similar to the previous one:

```javascript
import {chan, take, put, go, timeout} from "js-csp";

let fixedBufferChan = chan(1);

go(function*(){
    yield put(fixedBufferChan, 42);
    console.log("first put completed!");
    yield put(fixedBufferChan, 42);
    console.log("second put completed!");
});

go(function*(){
    console.log("waiting a second");
    yield timeout(1000);
    yield fixedBufferChan;
    console.log("take completed!");
});

//=> "first put completed!"
//=> "waiting a second"
//=> "take completed!"
//=> "second put completed!"
```

As you can see, a channel with a fixed buffer and no pending takes can accept up to `n` puts that
will be completed immediately before queueing put operations, where `n` is the size of the fixed
buffer.

### Dropping

The following two buffer types always accept values so if you use them you'll never have pending
puts. They differ in how they handle the overflow of values, since both are bounded.

A dropping buffer of size `n` will hold at most `n` elements and will always accept new values. When
we add a value to a dropping buffer and it has `n` elements, it will drop the value we just added, efectively
dropping it.

Let's see an example:

```javascript
import {chan, take, put, go, timeout, buffers} from "js-csp";

let droppingBufferChan = chan(buffers.dropping(2));

go(function*(){
    yield put(droppingBufferChan, 42);
    console.log("first put completed!");
    yield put(droppingBufferChan, 43);
    console.log("second put completed!");
    yield put(droppingBufferChan, 44);
    console.log("third put completed!");
});

go(function*(){
    console.log("waiting a second");
    yield timeout(1000);
    console.log("take completed:", yield droppingBufferChan);
    console.log("take completed:", yield droppingBufferChan);
    console.log("take completed:", yield droppingBufferChan);

});

//=> "first put completed!"
//=> "second put completed!"
//=> "third put completed!"
//=> "waiting a second"
//=> "take completed: 42"
//=> "take completed: 43"
```

As you can see, all puts got accepted immediately but only the first two made it into the channel's buffer.
When trying to take a third value from the channel in the second goroutine, the operation didn't succeed and "blocked".

### Sliding

A sliding buffer of size `n` will hold at most `n` elements and will always accept new values. When
we add a value to a sliding buffer and it has `n` elements it will drop the oldest value that got added,
so the buffer is a bounded window of values.

Let's see an example:

```javascript
import {chan, take, put, go, timeout, buffers} from "js-csp";

let slidingBufferChan = chan(buffers.sliding(2));

go(function*(){
    yield put(slidingBufferChan, 42);
    console.log("first put completed!");
    yield put(slidingBufferChan, 43);
    console.log("second put completed!");
    yield put(slidingBufferChan, 44);
    console.log("third put completed!");
});

go(function*(){
    console.log("waiting a second");
    yield timeout(1000);
    console.log("take completed:", yield slidingBufferChan);
    console.log("take completed:", yield slidingBufferChan);
    console.log("take completed:", yield slidingBufferChan);
});

//=> "first put completed!"
//=> "second put completed!"
//=> "third put completed!"
//=> "waiting a second"
//=> "take completed: 43"
//=> "take completed: 44"
```

As you can see, all puts got accepted immediately but only the last two made it into the channel's buffer.
When trying to take a third value from the channel in the second goroutine, the operation didn't succeed and "blocked".

### Promise

The last buffer available in `js-csp` is the promise buffer. A promise buffer will always accept values, but only
the first will be taken into account. Once the first value has been put, the buffer will always contain such element
and takes on that channel will immediately succeed and return such value.

It's analogous to the familiar Promise abstraction, where you only write one value that can be read many times. Let's
see an example:

```javascript
import {chan, take, put, go, timeout, buffers} from "js-csp";

let promiseBufferChan = chan(buffers.promise());

go(function*(){
    console.log("waiting half a second");
    yield timeout(500);
    yield put(promiseBufferChan, 42);
});

go(function*(){
    console.log("waiting a quarter of a second");
    yield timeout(250);
    yield put(promiseBufferChan, 99);
});

go(function*(){
    console.log("waiting a second");
    yield timeout(1000);
    console.log("take completed:", yield promiseBufferChan);
    console.log("take completed:", yield promiseBufferChan);
    console.log("take completed:", yield promiseBufferChan);
});

//=> "waiting half a second"
//=> "waiting a quarter of a a second"
//=> "waiting a second"
//=> "take completed: 99"
//=> "take completed: 99"
//=> "take completed: 99"
```

As you can see, all the puts and takes succeeded. The first value that was put (99) was delivered to every taker.

## Further information

- `js-csp`'s [documentation on channels](https://github.com/ubolonton/js-csp/blob/master/doc/basic.md#channels)
- Rich Hickey's [talk about `core.async` channel internals](https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/ImplementationDetails.md)
- Timothy Baldridge's video [about `core.async` channel internals](https://www.youtube.com/watch?v=WSgg-TQLsdw)
