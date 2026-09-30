import React from 'react';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { createStore, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import rootReducer from './rootReducer';

export function renderWithStore(ui, { preloadedState } = {}) {
  const store = createStore(rootReducer, preloadedState, applyMiddleware(thunk));
  return { store, ...render(<Provider store={store}>{ui}</Provider>) };
}
