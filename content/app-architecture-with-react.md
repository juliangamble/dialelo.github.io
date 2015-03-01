Title: Application Architecture with React: rethinking Flux
Category: JavaScript

TODO:

- Better title?
- Convert examples to ES6 module syntax
- Show simple pubsub implementation using js-csp?
- Cover testing of each abstraction?
- Write a small application putting all this together and push it to a GitHub repo

# Abstract

People coming to [React](http://facebook.github.io/react/) from other frameworks/libraries
tend to ask themselves how to manage application state since React only solves the UI rendering
problem, leaving the choice of state management and application architecture to the developer.
Facebook suggest an approach they call [Flux](http://facebook.github.io/flux/) for organizing
applications and managing their state.

In this article I will explore a way to manage state in JavaScript applications using
React as their UI layer and recast Facebook's Flux conceptual framework using ideas
from [ClojureScript](https://github.com/clojure/clojurescript) libraries like [Om](https://github.com/omcljs/om).

## Flux

Flux's core idea is that [data should flow in one direction](http://facebook.github.io/flux/docs/overview.html#structure-and-data-flow).
This makes reasoning about applications easier, dependencies between system components are well-defined and all
state changes come from a "single source of truth", as they put it.

In a nutshell: [Views](http://facebook.github.io/flux/docs/overview.html#views-and-controller-views)
trigger [Actions](http://facebook.github.io/flux/docs/overview.html#actions) which are notified to [Stores](http://facebook.github.io/flux/docs/overview.html#stores)
by a [Dispatcher](http://facebook.github.io/flux/docs/dispatcher.html#content).
Stores respond to actions modifying their state. Since views consume data from Stores and display it,
Store updates trigger re-renders in the UI when needed.

There are several things I dislike about Flux, namely:

- It complects state management and the bussiness logic for causing state changes.
- State is scattered through various stores which are apparently modular albeit they end up
  knowing about each other.
- The stores are coupled with the dispatching mechanism and actions that can happen on the
  system.

## From Stores to Global immutable state

Instead of having multiple stores, I suggest Om's approach of having a global mutable reference
to an immutable data structure. This way we model our application state as a succesion of immutable
values, without modifying data in-place or rebinding variables to different values.

This can be easily achieved using my [atomo](https://github.com/dialelo/atomo) library and Facebook's
[immutable-js](https://github.com/facebook/immutable-js).
The data structure contained in the global atom would be a map, which gives us the ability to
split data into separate logical domains using keys.

This approach doesn't try to hide the fact that separate logical domains tend to refer to each other,
here is a contrived example of the shape of a music application state:

```javascript
// state.js

let immutable = require("immutable");

let initialState = immutable.fromJS({
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
let atomo = require("atomo");

let state = atomo.atom(initialState);
```

Since atoms are observable and the immutable values they refer to share structure when creating
a new, modified value out of them, we can serialize the states our application in a memory-efficient
way:

```javascript
let history = atomo.atom(new immutable.List());

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
let kurtsore = require("kurtsore");

let cursor = kurtsore.cursor(state),
    albums = cursor.derive('albums'),
    playlists = cursor.derive('playlists');

immutable.is(
    albums.deref(),
    state.deref().get('albums')
);
//=> true

immutable.is(
    playlists.deref(),
    state.deref().get('playlists')
);
//=> true
```

## Views

We can create a cursor without a path for the top-level component, and refine it when passing it to
sub-components. With this approach we can have modular views that represent a substructure of the global
immutable state without knowing about the overall state.

Here is an example of a component that displays a sub-component of the global state and passes refined
cursors to its children:

```javascript
// views.js

let Album = React.createClass({
    render: function(){
        let album = this.props.album.deref();
        return <li>{album.get('artist')} - {album.get('title')}</li>;
    }
});

let Albums = React.createClass({
    render: function(){
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

Since cursors save a snapshot of the state they point to when created and immutable data
equality checks are blazing fast since they are just a reference comparison, they allow us to know
whether a component should update and implement a very efficient `shouldComponentUpdate`. You
can see an example in my [react-kurtsore](https://github.com/dialelo/react-kurtsore) library
and other open source libraries such as [Omniscient](https://github.com/omniscientjs/omniscient).

## Getting rid of the dispatcher

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
values that share the given topic will be put. If our actions are a immutable data structure with `type` and
`payload` fields, we could subscribe to actions with the approach shown below:

```javascript
import csp from "js-csp";
import pubsub from "./pubsub";

let userChan = csp.chan(),
    pub = pubsub.publication((v) => v.get("type"));

pub.sub("user:log-in", userChan);
pub.sub("user:log-out", userChan);

csp.go(function*(){
    let action = yield userChan;

    while (userChan !== csp.CLOSED) {
        let actionType = action.get("type"),
            user = action.get("payload");

        if (actionType === "user:log-in") {
            console.log(user, " just logged in.")
        } else  {
            console.log(user, " just logged out.");
        }

        action = yield userChan;
    }
});
```

The `userChan` above is channel that will receive log-in and log-out actions published to the system;
the generator passed to `go` will run indefinitely, listening for the actions that `userChan` receives
and logging those events to the console. Note that the generator passed to `go` will only resume when
`userChan` has values available, so it's safe to use a while loop inside it.

## Actions

As in Flux, actions can be identified with unique and constant values. For this we can use strings
or ES6 symbols. Since some actions may require asynchronous computations to get the data they need
and for the sake of decoupling views from the actions and the dispatch machinery, we encapsulate action
triggering in high-level APIs that the views can consume. Flux calls this high-level APIs action creators.

```javascript
// actions.js

let pubsub = require("./pubsub"),
    immutable = require("immutable");

let ADD_ALBUM = "albums:add";

let addAlbum = function(album){
    // you may do async work here!
    pubsub.publish(ADD_ALBUM, immutable.fromJS(album));
};
```

We'll go into more detail on the `pubsub` below, the important thing to note here is that the action payload is
immutable.

I suggest to encapsulate every action publication in one of these functions instead of publishing
actions from the views themselves because it decouples views from the system's communication machinery.
We also gain the benefit of testing views in isolation since we can interact with them and make sure they
consume our high-level APIs in the way they are supposed to.


### Interpreting actions out of stores

Having a pub-sub mechanism in place allows us to encapsulate state transitions
into small pieces. These can listen for specific actions (or combinations of actions) on the
pub-sub and affect the state accordingly, isolating bussines logic into modular and testable units I
call _effects_.

```javascript
// effects.js

let actions = require("./actions"),
    pubsub = require("./pubsub");

function addAlbum(pubSub, state){
    pubSub.subscribe(actions.ADD_ALBUM, function(album){
        albums.swap(function(albumList){
            return albumList.push(album);
        });
    });
};

module.exports.start = function(pubsub, state){
    addAlbum(pubsub, state);
    // more effects here
};
```

## Putting it all together

With all of the above, here is an example of how the entry point of an application could
look like:

TODO: Explain the bootstrap process better

```javascript
// main.js

let st = require("./state"),
    {Albums, Playlists} = require("./views"),
    pubsub = require("./pubsub"),
    effects = require("./effects"),
    React = require("react");

let App = React.createClass({
    render: function(){
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

function bootstrap(){
    // State
    let state = atomo.atom(st.initialState);

    // View
    render(kurtsore.cursor(state));
    state.addWatch(() => render(kurtsore.cursor(state)));

    // Effects
    effects.start(pubsub, state);
};

bootstrap();
```

### Further reading

TODO
