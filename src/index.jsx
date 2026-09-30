import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux'
import configureStore from './store';

import './index.css';
import App from './App';

ReactDOM.render(
  <React.StrictMode>
    <Provider store={configureStore()}>
		<App />
	</Provider>
  </React.StrictMode>,
  document.getElementById('root')
);

// This app no longer ships a service worker; remove any left registered by an older build.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(reg => reg.unregister()));
}
