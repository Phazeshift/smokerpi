import React from 'react';
import {
    BrowserRouter as Router,
    Switch,
    Route,
    Link
  } from "react-router-dom";
  import MyNavBar from './NavBar';
  import Home from './home'
  import Config from './config'
  
  export default function App() {
    return (
      <Router>
          <MyNavBar appTitle='SmokerPi' />
        <div>  
          {/* A <Switch> looks through its children <Route>s and
              renders the first one that matches the current URL. */}
          <Switch>            
            <Route path="/config">
              <Config />
            </Route>
            <Route path="/">
              <Home />
            </Route>
          </Switch>
        </div>
      </Router>
    );
  }