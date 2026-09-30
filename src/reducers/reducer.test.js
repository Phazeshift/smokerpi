import reducer from './reducer';
import {
  LOAD_GRAPH_DATA_SUCCESS,
  LOAD_CONFIG_DATA_SUCCESS,
  LOAD_STATE_DATA_SUCCESS,
  SOCKET_MESSAGE_RECEIVED,
  API_ERROR,
  API_ERROR_DISMISSED,
} from '../actions/actions';

describe('reducer', () => {
  test('returns the initial state for an unknown action', () => {
    const state = reducer(undefined, { type: '@@INIT' });
    expect(state).toEqual({ graphData: [], graphIndex: 0 });
  });

  test('LOAD_GRAPH_DATA_SUCCESS appends new points and advances graphIndex', () => {
    const initial = { graphData: [{ i: 0, t: 20 }], graphIndex: 1 };
    const state = reducer(initial, {
      type: LOAD_GRAPH_DATA_SUCCESS,
      data: [{ i: 1, t: 21 }, { i: 2, t: 22 }],
    });
    expect(state.graphData).toEqual([{ i: 0, t: 20 }, { i: 1, t: 21 }, { i: 2, t: 22 }]);
    expect(state.graphIndex).toBe(3);
  });

  test('LOAD_GRAPH_DATA_SUCCESS on an empty store resets graphIndex to 1', () => {
    const state = reducer(undefined, {
      type: LOAD_GRAPH_DATA_SUCCESS,
      data: [{ i: 0, t: 20 }],
    });
    expect(state.graphIndex).toBe(1);
  });

  test('LOAD_CONFIG_DATA_SUCCESS stores the config under state.config', () => {
    const state = reducer(undefined, {
      type: LOAD_CONFIG_DATA_SUCCESS,
      data: { set_temperature: 110 },
    });
    expect(state.config).toEqual({ set_temperature: 110 });
  });

  test('LOAD_STATE_DATA_SUCCESS stores the hardware state under state.state', () => {
    const state = reducer(undefined, {
      type: LOAD_STATE_DATA_SUCCESS,
      data: { temperature: 105, blower: 100 },
    });
    expect(state.state).toEqual({ temperature: 105, blower: 100 });
  });

  test('SOCKET_MESSAGE_RECEIVED merges the payload into the top-level state', () => {
    const initial = { graphData: [], graphIndex: 0, state: { temperature: 90 } };
    const state = reducer(initial, {
      type: SOCKET_MESSAGE_RECEIVED,
      payload: { state: { temperature: 95 } },
    });
    expect(state.state).toEqual({ temperature: 95 });
    expect(state.graphData).toEqual([]);
  });
  describe('API errors', () => {
    test('API_ERROR stores the message under state.error', () => {
      const state = reducer(undefined, { type: API_ERROR, message: 'Error calling api: boom' });
      expect(state.error).toBe('Error calling api: boom');
      expect(state.graphData).toEqual([]);
    });

    test('API_ERROR_DISMISSED removes the error', () => {
      const initial = { graphData: [], graphIndex: 0, error: 'boom' };
      const state = reducer(initial, { type: API_ERROR_DISMISSED });
      expect(state).toEqual({ graphData: [], graphIndex: 0 });
      expect('error' in state).toBe(false);
    });

    test('API_ERROR_DISMISSED with no error returns the same state object', () => {
      const initial = { graphData: [], graphIndex: 0 };
      expect(reducer(initial, { type: API_ERROR_DISMISSED })).toBe(initial);
    });

    test.each([
      ['LOAD_GRAPH_DATA_SUCCESS', LOAD_GRAPH_DATA_SUCCESS, []],
      ['LOAD_CONFIG_DATA_SUCCESS', LOAD_CONFIG_DATA_SUCCESS, {}],
      ['LOAD_STATE_DATA_SUCCESS', LOAD_STATE_DATA_SUCCESS, {}],
    ])('%s clears a previous error', (_name, type, data) => {
      const initial = { graphData: [], graphIndex: 0, error: 'boom' };
      const state = reducer(initial, { type, data });
      expect('error' in state).toBe(false);
    });
  });
});
