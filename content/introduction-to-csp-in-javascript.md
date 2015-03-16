Title: Introduction to Communicating Sequential Processes in JavaScript
Category: JavaScript

The JavaScript programming language features a rich set of techniques
for dealing with asynchronous computation. Raw [Continuation Passing Style (CPS) ](http://en.wikipedia.org/wiki/Continuation-passing_style)
with callbacks, [promises](http://en.wikipedia.org/wiki/Futures_and_promises) and
[Functional Reactive Programming](http://en.wikipedia.org/wiki/Functional_reactive_programming) are commonplace in today's JS.
EcmaScript 7 will bring syntantic sugar on top of promises with `async` and `await` and you can use that today with
[Babel](http://babeljs.io/).

However, the [Go](https://golang.org/) and [Clojure(Script)](https://github.com/clojure/clojurescript) programming languages
have popularized modern incarnations of [Tony Hoare's](http://es.wikipedia.org/wiki/C._A._R._Hoare)
[Communicating Sequential Processes (CSP)](http://en.wikipedia.org/wiki/Communicating_sequential_processes), which is a great substrate for representing
async computations and is backed by mathematical formalism. This article is intended as an introduction to CSP using the [js-csp](https://github.com/ubolonton/js-csp)
library, which is a straight port of the fantastic Clojure(Script) [core.async](https://github.com/). We'll
explore the aforementioned alternatives and talk about their strengths and weaknesses. After that we'll
delve into the building blocks of CSP: channels and processes; and show some examples of what you can do with such
primitives.

## Continuation Passing Style

The most common way of doing asynchronous computation in JavaScript has traditionally been continuation passing
style, using callbacks for continuing async calls. This approach is prevalent in many of the APIs we use as JavaScript
programmers, we can find examples in the browser, node and many existing libraries. The error handling is done either
accepting an error argument in the continuation or providing **two** continuations, one for succesful results and another for errors.

For a contrived example, let's assume that we have to make two calls to asynchronous functions, one called `getUserToken`
for getting a authentication token and another to `getUserInfo` that needs to be authenticated with the token, we then log
the user avatar URL to the console. Both functions accept success and error continuation as the last two arguments.

```javascript
import {getUserToken, getUserInfo} from "./user-cps";

let username = "Ada Byron",
    password = "I invented programming";

let onError = (err) => console.error(err);

getUserToken(username, password, (token) => {
    getUserInfo(token, (userInfo) => {
        console.log(userInfo['avatar']);
    }, onError);
}, onError);
```

Althoug our logic is very simple the callback machinery obscures it and the effort required to understand what's
going on is a lot more than it should be. Continuation passing style is very low-level and I think that most people will
agree that we need better abstractions on top of that. Luckily it's easy to transform functions written in continuation
passing style to offer a nicer inteface.

## Promises

Promises have slightly improved on CPS offering a first-class notion of asynchronous computations that may fail. There are
many promise libraries available and since it has become so widespread ES6 is shipping them as part of the standard. If our
`getUserToken` and `getUserInfo` function returned promises, we could transform the above example to this:

```javascript
import {getUserToken, getUserInfo} from "./user-promises";

let username = "Ada Byron",
    password = "I invented programming";

getUserToken(username, password)
   .then((token) => getUserInfo(token))
   .then((userInfo) => {
        console.log(userInfo['avatar']);
    })
   .catch((err) => console.error(err));
```

Promises obscure our logic too since we have to scatter a logical piece of functionality in multiple unrelated small functions.
On top of that, the `then` method [complects](http://en.wiktionary.org/wiki/complect) `map`ping a transforming function over the
value contained in a Promise with sequencing (`flatMap`) computations that return promises.

### async/await

ES7's `async` and `await` keywords let us express asynchronous computations using promises in a much more clear way, solving the
problem of obscured logic I talked before. We can declare a function as `async` and "block" for promises using the `await` keyword:

```javascript
import {getUserToken, getUserInfo} from "./user-promises";

async function() {
    let username = "Ada Byron",
        password = "I invented programming";

    try {
        let token = await getUserToken(username, password);
        let userInfo = await getUserInfo(token);
        console.log(userInfo['avatar']);
    } catch (err) {
        console.error(err);
    }
}
```

In my opinion this is much more clear and, as mentioned before, we can use it today with translators such as [Babel](http://babeljs.io/).

## Reactive streams

This is an unfair comparison since reactive streams represent a continuum of observable values instead of an
asynchronous computation with a single value like promises. Streams are a great abstraction and you can manipulate
them using a myriad of combinators, I recommend you to take a look at them. I'll be using [Bacon.js](https://baconjs.github.io/) for converting
our CPS functions into streams:

```javascript
import Bacon from "baconjs";
import {getUserToken, getUserInfo} from "./user-cps";

let username = "Ada Byron",
    password = "I invented programming";

Bacon.fromCallback(getUserToken, username, password)
     .flatMap((token) => Bacon.fromCallback(getUserInfo, token))
     .map((userInfo) => userInfo['avatar'])
     .log()
     .onError((err) => console.error(err))
```

Streams still scatter our logic but they separate value transformation (`map`) from sequencing (`flatMap`), although
it may depend on the implementation you are using.

## CSP

I'll go into detail about CSP below but before that let's revisit our example. `async` and `await` are designed with
promises in mind but we can get a similar syntactic abstraction using generators. Now our `getUserToken` and `getUserInfo`
functions will return channels, and they will put the value computed asynchronously in the channels they return:

```javascript
import {go} from "js-csp";
import {getUserToken, getUserInfo} from "./user-csp";


go(function*(){
    let username = "Ada Byron",
        password = "I invented programming";

    try {
        let token = yield getUserToken(username, password);
        let userInfo = yield getUserInfo(token);
        console.log(userInfo['avatar']);
    } catch (err) {
        console.error(err);
    }
});
```

As you can see, it's fairly similar to the example of promises with `async` and `await`. Let's dive into
the abstractions that CSP gives us for asynchronous computation to understand the above example better.

## Channels

Channels are first class queue-like objects, multiple readers and writers can either take or put one value at
a time on them. Their responsability is twofold: conveyance of values and synchronization. They decouple producers
of values from consumers and are the message-passing primitive of CSP. Channels are unbuffered by default but we can
create channels with different buffers, each with its own synchronization semantics.

Let's explore channels and their operations:

```javascript
import {chan, putAsync, takeAsync} from "js-csp";

let ch = chan();

takeAsync(ch, (value) => console.log("Got ", value));

// `ch` now has a pending take, let's try putting a value in it
putAsync(ch, 42);
//=> "Got 42"
```

Puts and takes can happen in any order:

```javascript
import {chan, putAsync, takeAsync} from "js-csp";

let ch = csp.chan();

// Async puts accept a callback too
putAsync(ch, 42, () => console.log("Just put 42"));
putAsync(ch, 43, () => console.log("One more"));

takeAsync(ch, (value) => console.log("Got ", value))
//=> "Got 42"
//=> "Just put 42"
takeAsync(ch, (value) => console.log("Got ", value))
//=> "Got 43"
//=> "One more"
```

Channels can be closed and after closing them the pending puts will fail, whereas pending takes will receive a special value
which signals that the channel is closed. Currently in js-csp such value is `null` so it's not allowed to put `null`
into a channel.

```javascript
import {chan, takeAsync, putAsync, CLOSED} from "js-csp";

let ch = chan();

takeAsync(ch, (value) => console.log("Channel closed? ", value === CLOSED));

putAsync(ch, 42);
//=> "Channel closed? false"

takeAsync(ch, (value) => console.log("Channel closed? ", value === CLOSED));
takeAsync(ch, (value) => console.log("Channel closed? ", value === CLOSED));

ch.close();
//=> "Channel closed? true"
//=> "Channel closed? true"
```

## Processes

The generator that we gave to the `go` function in the example above is a **process**, a piece of logic that uses
channels for communication and synchronization. Puts and takes on a process will "block" until the operation
completes, that's why we have to use `yield` when calling them. If we `yield` a channel an implicit take is performed.

```javascript
import {go, chan, put, take} from "js-csp";

let ch = chan();

go(function*(){
    console.log("[a] Starting a goroutine");
    let value = yield take(ch); // equivalent to 'yield ch'
    console.log("[a] Got ", value);
});

go(function*(){
    console.log("[b] Starting another goroutine");
    yield put(ch, 42);
});

//=> "[a] Starting a goroutine"
//=> "[b] Starting another goroutine"
//=> "[a] Got 42"
```

As we can see in the example above goroutines are a form of cooperative multitasking, they use channels for communication
and channel operations for context switching. We can create thousands of these lightweight processes in our programs and coordinate via channels.

### Choice

A cool thing about channels is that, given multiple channel operations, we can perform a non-determinismic choice between those
operations. In the Go programming language such construct is called `select`, probably after POSIX's [select](http://linux.die.net/man/2/select)
system call, and in `js-csp` is a function called `alts`. An important thing to note is that **only one** of the operations given to
`alts` will suceed and in case multiple operations are ready to be performed when calling it the successful operation will be
chosen pseudo-randomly by default.

Combined with `js-csp`'s `timeout` function, which returns a channel that won't receive any value and close after the
given amount of milliseconds, we can execute operations on a channel given they can be performed fast enough:

```javascript
import {chan, go, timeout, put, alts} from "js-csp";

let ch = chan();

go(function*(){
    console.log("[a] Gonna sleep for a second");
    yield timeout(1000);
    console.log("[a] Now I'm ready to put a value");
    yield put(ch, 42);
});

go(function*(){
    let cancel = timeout(300);

    // `alts` returns an object with the channel on which the operation has been
    // performed and its result
    let {channel, result} = yield alts([ch, cancel]);

    if (channel === cancel) {
        console.log("[b] Too slow, take was cancelled");
    } else {
        console.log("[b] Got ", result);
    }
});

//=> "[a] Gonna sleep for a second"
//=> "[a] Now I'm ready to put a value"
//=> "[b] Too slow, take was cancelled"
```

## Conclusion

We barely scratched the surface of what you can do with CSP in this article but I hope this introduction has served to
get you excited about it. I plan to write more on the topic, there are many things that I didn't cover for the sake of
brevity. I'm not claiming that CSP is superior to promises or reactive streams or that you should prefer it over them,
it's about knowing the abstractions you can use for expressing asynchronous computations and choosing the one that fits
the problem better and yields a simpler solution.

In future articles I plan to cover more topics related to CSP in JavaScript, which will include:

- Buffering strategies
- Using transducers with channels
- High-level patterns on top of CSP
- UI component decoupling with channels
- CSP-flavored Functional Reactive Programming

## Further reading

- [Taming the Async beast with ES7](http://pouchdb.com/2015/03/05/taming-the-async-beast-with-es7.html)
- [Taming the Async beast with CSP in JavaScript](http://jlongster.com/Taming-the-Asynchronous-Beast-with-CSP-in-JavaScript)
- [Make no promises](http://swannodette.github.io/2013/08/23/make-no-promises/)
- [ES6 generators and CSP](http://swannodette.github.io/2013/08/24/es6-generators-and-csp/)
