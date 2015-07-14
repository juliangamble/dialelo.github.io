Title: Application Architecture with React: rethinking Flux
Category: JavaScript

People coming to [React](http://facebook.github.io/react/) from other frameworks/libraries
tend to ask themselves how to manage application state since React only solves the UI rendering
problem, leaving the choice of state management and application architecture to the developer.
Facebook suggest an architecture called [Flux](http://facebook.github.io/flux/) that fits
with the React rendering model.

In this article I will explore a way to manage state in JavaScript applications using
React as their UI layer and recast Facebook's Flux conceptual framework using ideas
from [ClojureScript](https://github.com/clojure/clojurescript) libraries like [Om](https://github.com/omcljs/om).

## Flux

Flux's core idea is that [data should flow in one direction](http://facebook.github.io/flux/docs/overview.html#structure-and-data-flow).
This makes reasoning about applications easier, dependencies between system components are well-defined and all
state changes come from a "single source of truth", as they put it.

![](http://facebook.github.io/flux/img/flux-simple-f8-diagram-explained-1300w.png)

In a nutshell: [Views](http://facebook.github.io/flux/docs/overview.html#views-and-controller-views)
trigger [Actions](http://facebook.github.io/flux/docs/overview.html#actions) which are notified to [Stores](http://facebook.github.io/flux/docs/overview.html#stores)
by a [Dispatcher](http://facebook.github.io/flux/docs/dispatcher.html#content).
Stores respond to actions modifying their state. Since views consume data from Stores and display it,
Store updates trigger re-renders in the UI when needed.

There are several things I dislike about Flux, namely:

- It complects state management and the bussiness logic for causing state changes.
- State is scattered through various stores which are apparently modular albeit they end up
  knowing about each other.
- The stores are coupled with the dispatching mechanism.


## From Stores to Global immutable state

Instead of having multiple stores, I suggest Om's approach of having a global mutable reference
to an immutable data structure. This way we model our application state as a succesion of immutable
values, without modifying data in-place or rebinding variables to different values over time.

This can be easily achieved using my [atomo](https://github.com/dialelo/atomo) library and Facebook's
[immutable-js](https://github.com/facebook/immutable-js).
The data structure contained in the global atom would be a map, which gives us the ability to
split data into separate logical domains using keys.

This approach doesn't try to hide the fact that separate logical domains tend to refer to each other,
here is a contrived example of the shape of a music application state:

```javascript
// state.js

import {fromJS} from "immutable";

let initialState = fromJS({
    user: null,
    albums: [
        {
            title: "La Leyenda del Tiempo",
            artist: "Camarón"
        },
        {
            title: "Veneno",
            artist: "Veneno"
        }
    ],
    playlists: [
        {
            name: "Flamenco",
            tracks: [
                {
                    title: "Nana del Caballo Grande",
                    artist: "Camarón",
                    album: "La Leyenda del Tiempo"
                }
            ]
        }
    ]
});
```

We can create the global mutable atom very easily from an immutable data structure:

```javascript
// state.js

import atomo from "atomo";

export const state = atomo.atom(initialState);
```

Since atoms are observable and the immutable values they refer to share structure when creating
a new, modified value out of them, we can serialize the states our application in a memory-efficient
way:

```javascript
// history.js

import {List} from "immutable";
import {state} from "./state";

const history = atomo.atom(new List());

state.addWatch(function(atom, oldValue, newValue){
    history.swap((hs) => hs.push(oldValue));
});
```

This gives us the ability of time-travelling for free, it's trivial to implement undo/redo functionality
on top of this state management strategy. If we were to serialize the succession of actions and their payload
in the system we would be able to replay a user interaction with our application very easily, making regression
testing as simple as feeding the aforementioned actions to the system and asserting that we end up with a consistent
state.

### Cursors

We don't want to be passing around all the state to every view. Views usually display a subset of the global state
so we need the ability to focus on paths inside the global immutable state for making our views modular.

Om solves this problem with an abstraction called [Cursor](https://github.com/omcljs/om/wiki/Cursors), which
lets us focus on a path of the global atom and offer the same API as atoms. This allows views to treat the substructure
as their data source and even modify it with the same operations as the Atom. I wrote a [simple
implementation](https://github.com/dialelo/kurtsore) of this concept for using it with atoms and immutable data.

We can derive a cursor from an atom or another cursor, allowing us to refine the path they point to:

```javascript
import kurtsore from "kurtsore";
import {is} from "immutable";

let cursor = kurtsore.cursor(state),
    albums = cursor.derive('albums'),
    playlists = cursor.derive('playlists');

is(
    albums.deref(),
    state.deref().get('albums')
);
//=> true

is(
    playlists.deref(),
    state.deref().get('playlists')
);
//=> true
```

## Views

We can create a cursor without a path for the top-level component, and refine it when passing it to
sub-components. With this approach we can have modular views that represent a substructure of the global
immutable state without knowing about the overall state.

Since cursors save a snapshot of the state they point to when created and immutable data
equality checks are blazing fast since they are just a reference comparison, they allow us to know
whether a component should update and implement a very efficient `shouldComponentUpdate`. You
can see an example in my [react-kurtsore](https://github.com/dialelo/react-kurtsore) library
and other open source libraries such as [Omniscient](https://github.com/omniscientjs/omniscient).

Here is an example of a component that displays a sub-component of the global state and passes refined
cursors to its children:

```javascript
// views.js

import React from "react";
import {CursorPropsMixin} from "react-kurtsore";


export const Album = React.createClass({
    mixins: [ CursorPropsMixin ],

    render(){
        let album = this.props.album.deref();
        return <li>{album.get('artist')} - {album.get('title')}</li>;
    }
});

export const Albums = React.createClass({
    mixins: [ CursorPropsMixin ],

    render(){
        let albums = this.props.albums.deref(),
            cursors = albums.map((a, idx) => this.props.albums.derive(idx));

        return (
            <ul>
                {cursors.map(
                    (a, idx) => <Album key={idx} album={a} />
                )}
            </ul>
        );
    }
});
```

## Actions

As in Flux, actions can be identified with unique and constant values. For this we can use strings
or ES6 symbols.

```javascript
//  constants.js

export const ACTIONS = {
    LOG_IN: Symbol.for("user:log-in"),
    LOG_IN_FAILED: Symbol.for("user:log-in-failed"),
    LOG_OUT: Symbol.for("user:log-out")
};
```

We represent actions as an immutable record with `type` and `payload` attributes,
where the type is the identifier constant and the payload can be an arbitrary immutable value.

```javascript
// actions.js

import immutable from "immutable";

export const Action = immutable.Record({type: null, payload: null});

export function action(type, payload){
    return new Action({type, payload});
};
```

### Getting rid of the dispatcher

Flux proposes the singleton Dispatcher coupled to stores for triggering state transitions. This introduces
dependencies between stores, making them know about each other and the order the actions must be processed
by each store. Dispatchers are also different from a pub-sub mechanism in that they fan-out every action
that is triggered on them to all the stores.

I instead suggest using [CSP](http://en.wikipedia.org/wiki/Communicating_sequential_processes) channels for
the actions pub-sub mechanism, which you get with the [js-csp](https://github.com/ubolonton/js-csp) library.

The pub-sub system has a channel in which actions are published, and we can derive a publication from it. The
publication takes the source channel and a function that extracts the "topic" of the messages put into the
source channel. For ease of testing we can make the source channel configurable using an atom:

```javascript
// pubsub.js

import atomo from "atomo";
import csp from "js-csp";

export const source = atomo.atom(csp.chan());

export function publication(topicFn){
    return csp.operations.pub.publication(source.deref(), topicFn);
};

export function publish(msg){
    csp.putAsync(source.deref(), msg);
};
```

The publication allows other components of the system to subscribe to a topic, providing a channel where the
values that share the given topic will be put. We can subscribe to actions with the approach shown below:

```javascript
import csp from "js-csp";
import pubsub from "./pubsub";
import {ACTIONS} from "./constants";

let userChan = csp.chan(),
    pub = pubsub.publication((v) => v.get("type"));

pub.sub(ACTIONS.LOG_IN, userChan);
pub.sub(ACTIONS.LOG_OUT, userChan);

csp.go(function*(){
    let action = yield userChan;

    while (action !== csp.CLOSED) {
        let {type} = action;

        if (type === ACTIONS.LOG_IN) {
            let user = action.get("payload");
            console.log(user, " just logged in.")
        } else {
            console.log("The user just logged out.");
        }

        action = yield userChan;
    }
});
```

The `userChan` above is channel that will receive log-in and log-out actions published to the system;
the generator passed to `go` will run indefinitely, listening for the actions that `userChan` receives
and logging those events to the console. Note that the generator passed to `go` will only resume when
`userChan` has values available, so it's safe to use a while loop inside it.

### Publishing actions

Since some actions may require asynchronous computations to get the data they need and for the sake of
decoupling views from the actions and the dispatch machinery, we encapsulate action
triggering in high-level APIs that the views can consume. Flux calls this high-level APIs action creators.

I suggest to encapsulate every action publication in one of these functions instead of publishing
actions from the views themselves because it decouples views from the system's communication machinery.
We also gain the benefit of testing views in isolation since we can interact with them and make sure they
consume our high-level APIs in the way they are supposed to.

```javascript
// authentication.js

import {ACTIONS} from "./constants";
import {action} from "./actions";
import pubsub from "./pubsub";
import http from "./http";
import {fromJS} from "immutable";


export function tryLogIn(username, password){
    http.post("/login", {username, password})
        .then((user) => pubsub.publish(action(ACTIONS.LOG_IN, fromJS(user))))
        .catch((errors) => pubsub.publish(action(ACTIONS.LOG_IN_FAILED, fromJS(errors))))
};

export function logout(username, password){
    pubsub.publish(action(ACTIONS.LOG_OUT));
};
```

### Interpreting actions

Having a pub-sub mechanism in place allows us to encapsulate state transitions
into small pieces. These can listen for specific actions (or combinations of actions) on the
pub-sub and affect the state accordingly, isolating bussines logic into modular and testable units I
call _effects_.

```javascript
// effects.js

import csp from "js-csp";
import {ACTIONS} from "./constants";


export function logIn(publication, state){
    let loginChan = csp.chan();

    publication.sub(ACTIONS.LOG_IN, loginChan);

    csp.go(function*(){
        let action = yield loginChan;

        while (action !== csp.CLOSED) {
            let user = action.get("payload");
            state.swap((st) => st.set('user', user))
            action = yield loginChan;
        }
    });

    return loginChan;
};

export function logOut(publication, state){
    let logoutChan = csp.chan();

    publication.sub(ACTIONS.LOG_OUT, logoutChan);

    csp.go(function*(){
        let action = yield logoutChan;

        while (action !== csp.CLOSED) {
            state.swap((st) => st.remove('user'))
            action = yield logoutChan;
        }
    });

    return logoutChan;
};

```

We can test `logIn` and `logOut` effects in isolation inyecting a publication and an atom.
Note that the `logIn` and `logOut` effects are started when calling them and return the channel they
listen to, giving us the ability to shut them down closing the channel. If we group together a set of effects we could
create a stateful object that allowed us to start and stop them at will.

```javascript
// effects.js

class Effects {
    start(publication, state){
        this.chans = [
            logIn(publication, state),
            logOut(publication, state)
        ];
    }
    stop(){
        this.chans.map((ch) => ch.close());
    }
}

export default new Effects();
```

## Putting it all together

With all of the above, here is an example of how the entry point of an application could
look like:

```javascript
// main.js

import React from "react";
import {CursorPropsMixin} from "react-kurtsore";

import {state} from "./state";
import {Albums, Playlists} from "./views";
import pubsub from "./pubsub";
import effects from "./effects";

const App = React.createClass({
    mixins: [ CursorPropsMixin ],

    render(){
        let state = this.props.state;

        return (
            <div>
                <Albums state={state.derive('albums')} />
                <Playlists state={state.derive('playlists')} />
            </div>
        );
    }
});

function render(state){
    React.render(<App state={state} />, document.querySelector("body"));
};

(function bootstrap(){
    // View
    render(kurtsore.cursor(state));
    state.addWatch(() => render(kurtsore.cursor(state)));

    // Pub-sub
    let publication = pubsub.publication((ac) => ac.get("type"));

    // Effects
    effects.start(publication, state);
})();
```

### Further reading

- [The Future of JavaScript MVC Frameworks](http://swannodette.github.io/2013/12/17/the-future-of-javascript-mvcs/)
- [Time Travel](http://swannodette.github.io/2013/12/31/time-travel/)
- [ES6 Generators and CSP](http://swannodette.github.io/2013/08/24/es6-generators-and-csp/)
- [Taming the Asynchronous Beast with CSP Channels in JavaScript](http://jlongster.com/Taming-the-Asynchronous-Beast-with-CSP-in-JavaScript)
