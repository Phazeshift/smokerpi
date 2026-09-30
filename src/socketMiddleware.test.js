import { socketMiddleware } from './socketMiddleware';

vi.mock('socket.io-client', () => ({
  default: { connect: vi.fn() },
}));

import io from 'socket.io-client';

function makeFakeSocket() {
  const handlers = {};
  return {
    on: vi.fn((event, handler) => {
      handlers[event] = handler;
    }),
    emit: vi.fn(),
    trigger: (event, payload) => handlers[event] && handlers[event](payload),
  };
}

describe('socketMiddleware', () => {
  test('dispatches SOCKET_MESSAGE_RECEIVED when the socket emits a message event', () => {
    const socket = makeFakeSocket();
    io.connect.mockReturnValue(socket);

    const store = { dispatch: vi.fn() };
    socketMiddleware('http://example.test')(store);

    expect(io.connect).toHaveBeenCalledWith('http://example.test');
    socket.trigger('message', { temperature: 105 });

    expect(store.dispatch).toHaveBeenCalledWith({
      type: 'SOCKET_MESSAGE_RECEIVED',
      payload: { temperature: 105 },
    });
  });

  test('SEND_WEBSOCKET_MESSAGE actions are emitted on the socket and not passed further down the chain', () => {
    const socket = makeFakeSocket();
    io.connect.mockReturnValue(socket);

    const store = { dispatch: vi.fn() };
    const next = vi.fn();
    const dispatchAction = socketMiddleware('http://example.test')(store)(next);

    const action = { type: 'SEND_WEBSOCKET_MESSAGE', method: 'update', payload: { foo: 'bar' } };
    const result = dispatchAction(action);

    expect(socket.emit).toHaveBeenCalledWith('update', { foo: 'bar' });
    expect(next).not.toHaveBeenCalled();
    expect(result).toBeUndefined();
  });

  test('other actions are passed through to the next middleware', () => {
    const socket = makeFakeSocket();
    io.connect.mockReturnValue(socket);

    const store = { dispatch: vi.fn() };
    const next = vi.fn(action => action);
    const dispatchAction = socketMiddleware('http://example.test')(store)(next);

    const action = { type: 'SOME_OTHER_ACTION' };
    dispatchAction(action);

    expect(next).toHaveBeenCalledWith(action);
  });
});
