import React from 'react';
import { screen } from '@testing-library/react';
import { renderWithStore } from './testUtils';
import Home from './home';

beforeEach(() => {
  fetch.resetMocks();
  fetch.mockResponse(JSON.stringify({}));
});

test('renders the status card, controls and graph together', () => {
  const preloadedState = {
    smokerpi: {
      graphData: [],
      graphIndex: 0,
      state: { temperature: 90, targetTemperature: 105, blower: 0, damper: 0, pid: false },
    },
  };

  renderWithStore(<Home />, { preloadedState });

  expect(screen.getByText('90°C')).toBeInTheDocument();
  expect(screen.getByText('Toggle Blower')).toBeInTheDocument();
});
