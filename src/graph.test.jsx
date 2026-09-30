import React from 'react';
import { renderWithStore } from './testUtils';
import Graph from './graph';

beforeEach(() => {
  fetch.resetMocks();
  fetch.mockResponse(JSON.stringify([]));
});

test('renders without crashing and fetches graph data on mount', () => {
  const preloadedState = {
    smokerpi: {
      graphIndex: 2,
      graphData: [
        { i: 0, x: '01/01/2024 00:00:00', t: 20, b: 0, d: 0, s: 105 },
        { i: 1, x: '01/01/2024 00:00:10', t: 21, b: 0, d: 0, s: 105 },
      ],
    },
  };

  renderWithStore(<Graph />, { preloadedState });

  expect(fetch).toHaveBeenCalledWith('/api/graph?from=2');
});
