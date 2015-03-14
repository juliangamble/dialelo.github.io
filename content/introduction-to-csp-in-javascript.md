Title: Introduction to Communicating Sequential Processes in JavaScript
Category: JavaScript
Status: Draft

The JavaScript programming language features a rich set of techniques and abstractions
for dealing with asynchronous computations. Raw continuation pasing style (CPS) with callbacks,
promises and reactive streams are commonplace in 2015's JS. ES7's plans to include syntantic sugar
on top of promises with `async` and `await` are behind the corner, and you can use that today with
Babel.

However, the Go and Clojure(Script) programming languages have popularized modern incarnations of
Sir Tony Hoare's Communicating Sequential Processes (CSP), which makes a great substrate for representing
async computations. This article is intended as an introduction to CSP using the [js-csp](https://github.com/ubolonton/js-csp)
library, which is a straight port of the fantastic Clojure(Script) [core.async](https://github.com/). We'll
explore the aforementioned alternatives and talk about their strengths and weaknesses to then
delve into the building blocks of CSP: channels and processes; show some examples of what you can do with such
primitives and compare CSP to the other asynchronous programming approaches.

## Continuation Passing Style

The most common way of doing asynchronous computation in JavaScript has traditionally been continuation passing
style, using callbacks for continuing async calls. This approach is prevalent in many of the browser APIs. The error
handling is done either accepting an error argument in the continuation or providing *two* continuations, one for
succesful results and another for errors.

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
agree that we need better abstractions on top of that. Sadly it's the way many APIs are designed but is easy to transform
this functions to offer a nicer inteface.

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
On top of that, the `then` method complects `map`ping the value contained in a Promise to transform it with sequencing (`flatMap`)
computations that return promises.

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

In my opinion this is much more clear and we can use it today with translators like Babel.

## Reactive streams

This is an unfair comparison since reactive streams represent a continuum of observable values instead of an
asynchronous computation with a single value like promises. Streams are a great abstraction and you can manipulate
them using a myriad of combinators, I recommend you to take a look at them. I'll be using Bacon.js for converting
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

first-class
conveyance/synchronization
multiple readers and writers/ put and take single value at a time

```javascript
```

## Processes

cooperative multitasking
channels as synchronization points

## Putting it all together

### Choice

non-determinism
timeouts

### Buffers

different synchronization policies

## Further reading

- http://pouchdb.com/2015/03/05/taming-the-async-beast-with-es7.html
- http://jlongster.com/Taming-the-Asynchronous-Beast-with-CSP-in-JavaScript
- http://swannodette.github.io/2013/08/23/make-no-promises/
- http://swannodette.github.io/2013/08/24/es6-generators-and-csp/
- http://swannodette.github.io/2013/07/31/extracting-processes/

## Conclusion

extracting async logic intro processes makes it context-independent
use the abstraction that better fits the problem you have to solve
