import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithStore } from './testUtils';
import StatusCard from './statuscard';

beforeEach(() => {
  fetch.resetMocks();
});

test('renders the current temperature and hardware state from the store', () => {
  const preloadedState = {
    smokerpi: {
      graphData: [],
      graphIndex: 0,
      state: { temperature: 107, targetTemperature: 105, blower: 100, damper: 40, pid: true },
    },
  };
  // avoid the componentDidMount refresh clobbering the values we asserted on
  fetch.mockResponse(JSON.stringify(preloadedState.smokerpi.state));

  renderWithStore(<StatusCard />, { preloadedState });

  expect(screen.getByText('107°C')).toBeInTheDocument();
  expect(screen.getByText(/Blower: 100/)).toBeInTheDocument();
  expect(screen.getByText(/Damper: 40/)).toBeInTheDocument();
  expect(screen.getByText(/Pid: On/)).toBeInTheDocument();
  expect(screen.getByText(/Target: 105/)).toBeInTheDocument();
});

test('fetches the current state on mount', () => {
  fetch.mockResponse(JSON.stringify({}));
  const preloadedState = { smokerpi: { graphData: [], graphIndex: 0, state: {} } };

  renderWithStore(<StatusCard />, { preloadedState });

  expect(fetch).toHaveBeenCalledWith('/api/state');
});


test('shows a worker error from the server', () => {
  const state = { temperature: 107, targetTemperature: 105, blower: 0, damper: 40, pid: true, workerError: 'temperature read: spi boom' };
  fetch.mockResponse(JSON.stringify(state));

  renderWithStore(<StatusCard />, { preloadedState: { smokerpi: { graphData: [], graphIndex: 0, state } } });

  expect(screen.getByRole('alert')).toHaveTextContent('temperature read: spi boom');
});

test('shows no alert when the worker is fine', () => {
  const state = { temperature: 107, targetTemperature: 105, blower: 0, damper: 40, pid: true, workerError: null };
  fetch.mockResponse(JSON.stringify(state));

  renderWithStore(<StatusCard />, { preloadedState: { smokerpi: { graphData: [], graphIndex: 0, state } } });

  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
