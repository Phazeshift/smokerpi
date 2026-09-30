import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { createStore, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import rootReducer from './rootReducer';
import App from './App';

beforeEach(() => {
  fetch.resetMocks();
  fetch.mockResponse(JSON.stringify({}));
});

function renderApp() {
  const store = createStore(rootReducer, applyMiddleware(thunk));
  return render(
    <Provider store={store}>
      <App />
    </Provider>
  );
}

test('renders the nav bar and the home page by default', () => {
  renderApp();
  expect(screen.getByText('SmokerPi')).toBeInTheDocument();
  expect(screen.getByText('Toggle Blower')).toBeInTheDocument();
});
