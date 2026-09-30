import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route
  } from "react-router-dom";
  import MyNavBar from './NavBar';
  import Home from './home';
  import Config from './config';
  
  export default function App() {
    return (
      <Router>
          <MyNavBar appTitle='SmokerPi' />
        <div>  
          {/* <Routes> renders the best-matching <Route> for the current URL;
              the "*" route keeps the old behaviour of showing Home for any other path. */}
          <Routes>
            <Route path="/config" element={<Config />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </div>
      </Router>
    );
  }