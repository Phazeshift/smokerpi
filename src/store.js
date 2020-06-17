import { createStore, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import logger from 'redux-logger';
import rootReducer from './rootReducer';
import { socketMiddleware } from './socketMiddleware';

export default function configureStore(url) {
 return createStore(
  rootReducer,
   applyMiddleware(thunk, logger, socketMiddleware(url))
 );
}