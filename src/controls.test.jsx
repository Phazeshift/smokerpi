import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithStore } from './testUtils';
import Controls from './controls';

beforeEach(() => {
  fetch.resetMocks();
  fetch.mockResponse(JSON.stringify({}));
});

const preloadedState = {
  smokerpi: { graphData: [], graphIndex: 0, state: { blower: 0, damper: 0, pid: false } },
};

test('clicking Toggle Blower posts to /api/blower', () => {
  renderWithStore(<Controls />, { preloadedState });

  fireEvent.click(screen.getByText('Toggle Blower'));

  expect(fetch).toHaveBeenCalledWith('/api/blower', expect.objectContaining({ method: 'POST' }));
});

test('clicking Toggle Damper posts to /api/damper', () => {
  renderWithStore(<Controls />, { preloadedState });

  fireEvent.click(screen.getByText('Toggle Damper'));

  expect(fetch).toHaveBeenCalledWith('/api/damper', expect.objectContaining({ method: 'POST' }));
});

test('clicking Toggle Pid posts to /api/pid', () => {
  renderWithStore(<Controls />, { preloadedState });

  fireEvent.click(screen.getByText('Toggle Pid'));

  expect(fetch).toHaveBeenCalledWith('/api/pid', expect.objectContaining({ method: 'POST' }));
});

test('clicking Update Graph fetches the latest graph data', () => {
  renderWithStore(<Controls />, { preloadedState });

  fireEvent.click(screen.getByText('Update Graph'));

  expect(fetch).toHaveBeenCalledWith('/api/graph?from=0');
});
