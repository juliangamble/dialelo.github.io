Title: React component communication with CSP channels
Category: JavaScript
Status: draft

```javascript
import csp from "js-csp";
import React from "react";

let Channel = csp.chan().constructor;

const Slider = React.createClass({
    propTypes: {
        in: React.PropTypes.instanceOf(Channel),
        out: React.PropTypes.instanceOf(Channel)
    },

    getInitialState(){
        return { progress: 0 }
    },

    componentWillMount(){
        let mixer = csp.operations.mix(this.props.in);
        this.setState({ mixer });

        csp.go(function*(){
            let progress = yield this.props.in;
            while (progress !== csp.CLOSED){
                this.setState({ progress });
                progress = yield this.props.in;
            }
        }.bind(this))
    },

    componentWillUnmount(){
        this.props.in.close();
        this.props.out.close();
    },

    render(){
        return <input type="range" min="0" max="100" step="1" value={this.state.progress * 100} />
    },

    shouldComponentUpdate(nextProps, nextState){
        return this.state.progress !== nextState.progress;
    }
});

```



### Further reading

- [ES6 Generators and CSP](http://swannodette.github.io/2013/08/24/es6-generators-and-csp/)
- [Taming the Asynchronous Beast with CSP Channels in JavaScript](http://jlongster.com/Taming-the-Asynchronous-Beast-with-CSP-in-JavaScript)
