import configureMockStore from 'redux-mock-store';
import { thunk } from 'redux-thunk';
const fetchMock = global.fetch;

import {
  getGraphData,
  getConfig,
  updateConfig,
  getCurrentState,
  toggleBlower,
  toggleDamper,
  toggleAutomatic,
  LOAD_GRAPH_DATA_SUCCESS,
  LOAD_CONFIG_DATA_SUCCESS,
  LOAD_STATE_DATA_SUCCESS,
  API_ERROR,
  API_ERROR_DISMISSED,
  dismissApiError,
} from './actions';

const mockStore = configureMockStore([thunk]);

// postApi's success callback dispatches a *second*, un-awaited thunk (e.g.
// updateConfig -> dispatch(getConfig())) to refresh state after a POST, so
// tests asserting on its effects need to let that floating promise settle.
const flushPromises = () => new Promise(resolve => setImmediate(resolve));

beforeEach(() => {
  fetchMock.resetMocks();
});

describe('getGraphData', () => {
  test('requests from the current graphIndex and dispatches the result', async () => {
    fetchMock.mockResponseOnce(JSON.stringify([{ i: 3, t: 22 }]));
    const store = mockStore({ smokerpi: { graphIndex: 3 } });

    await store.dispatch(getGraphData());

    expect(fetchMock).toHaveBeenCalledWith('/api/graph?from=3');
    expect(store.getActions()).toEqual([
      { type: LOAD_GRAPH_DATA_SUCCESS, data: [{ i: 3, t: 22 }] },
    ]);
  });
});

describe('getConfig / getCurrentState', () => {
  test('getConfig dispatches LOAD_CONFIG_DATA_SUCCESS on success', async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ set_temperature: 105 }));
    const store = mockStore({});

    await store.dispatch(getConfig());

    expect(store.getActions()).toEqual([
      { type: LOAD_CONFIG_DATA_SUCCESS, data: { set_temperature: 105 } },
    ]);
  });

  test('getCurrentState dispatches LOAD_STATE_DATA_SUCCESS on success', async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ temperature: 100 }));
    const store = mockStore({});

    await store.dispatch(getCurrentState());

    expect(store.getActions()).toEqual([
      { type: LOAD_STATE_DATA_SUCCESS, data: { temperature: 100 } },
    ]);
  });

  test('an HTTP error dispatches API_ERROR instead of the success action', async () => {
    fetchMock.mockResponseOnce('', { status: 500, statusText: 'Internal Server Error' });
    const store = mockStore({});

    await store.dispatch(getConfig());

    expect(store.getActions()).toEqual([
      { type: API_ERROR, message: 'Error calling api: Internal Server Error' },
    ]);
  });

  test('a network failure (API unreachable) dispatches API_ERROR', async () => {
    fetchMock.mockRejectOnce(new Error('Failed to fetch'));
    const store = mockStore({});

    await store.dispatch(getCurrentState());

    expect(store.getActions()).toEqual([
      { type: API_ERROR, message: 'Error calling api: Failed to fetch' },
    ]);
  });

  test('a failed POST dispatches API_ERROR and does not refresh state', async () => {
    fetchMock.mockResponseOnce('', { status: 500, statusText: 'Internal Server Error' });
    const store = mockStore({ smokerpi: { state: { blower: 0 } } });

    await store.dispatch(toggleBlower());
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(store.getActions()).toEqual([
      { type: API_ERROR, message: 'Error calling api: Internal Server Error' },
    ]);
  });
});

test('dismissApiError creates the dismiss action', () => {
  expect(dismissApiError()).toEqual({ type: API_ERROR_DISMISSED });
});

describe('toggle thunks', () => {
  test('toggleBlower posts the inverse of the current state and refreshes state', async () => {
    fetchMock
      .mockResponseOnce(JSON.stringify({}))
      .mockResponseOnce(JSON.stringify({ blower: 0 }));
    const store = mockStore({ smokerpi: { state: { blower: 100 } } });

    await store.dispatch(toggleBlower());
    await flushPromises();

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/blower');
    expect(JSON.parse(opts.body)).toEqual({ enabled: false });
    expect(store.getActions()).toEqual([
      { type: LOAD_STATE_DATA_SUCCESS, data: { blower: 0 } },
    ]);
  });

  test('toggleDamper posts the inverse of the current state', async () => {
    fetchMock
      .mockResponseOnce(JSON.stringify({}))
      .mockResponseOnce(JSON.stringify({ damper: 100 }));
    const store = mockStore({ smokerpi: { state: { damper: 0 } } });

    await store.dispatch(toggleDamper());

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/damper');
    expect(JSON.parse(opts.body)).toEqual({ enabled: true });
  });

  test('toggleAutomatic posts the inverse of the current pid flag', async () => {
    fetchMock
      .mockResponseOnce(JSON.stringify({}))
      .mockResponseOnce(JSON.stringify({ pid: true }));
    const store = mockStore({ smokerpi: { state: { pid: false } } });

    await store.dispatch(toggleAutomatic());

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/pid');
    expect(JSON.parse(opts.body)).toEqual({ enabled: true });
  });
});

describe('updateConfig', () => {
  test('posts the given config and re-fetches it on success', async () => {
    fetchMock
      .mockResponseOnce(JSON.stringify({}))
      .mockResponseOnce(JSON.stringify({ set_temperature: 130 }));
    const store = mockStore({});

    await store.dispatch(updateConfig({ set_temperature: 130 }));
    await flushPromises();

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/config');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ set_temperature: 130 });
    expect(store.getActions()).toEqual([
      { type: LOAD_CONFIG_DATA_SUCCESS, data: { set_temperature: 130 } },
    ]);
  });
});
