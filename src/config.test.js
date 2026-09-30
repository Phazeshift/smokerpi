import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithStore } from './testUtils';
import Config from './config';

const fullConfig = {
  cs_pin: 20,
  clock_pin: 21,
  data_pin: 16,
  blower_pin1: 26,
  blower_pin2: 19,
  damper_pin: 13,
  set_temperature: 105,
  graph_interval: 10,
  worker_interval: 10,
  blower_minimum: 40,
  damper_minimum: 500,
  damper_maximum: 2500,
};

beforeEach(() => {
  fetch.resetMocks();
  fetch.mockResponse(JSON.stringify(fullConfig));
});

function renderConfig() {
  return renderWithStore(<Config />, {
    preloadedState: { smokerpi: { graphData: [], graphIndex: 0, config: fullConfig } },
  });
}

test('renders the form pre-filled with the current config', () => {
  renderConfig();

  expect(screen.getByLabelText('Target temperature')).toHaveValue('105');
  expect(screen.getByLabelText('Blower minimum')).toHaveValue('40');
});

test('clearing the required target temperature hides the Save button, so an empty value can never be submitted', () => {
  renderConfig();
  fetch.mockClear();

  fireEvent.change(screen.getByLabelText('Target temperature'), { target: { value: '' } });

  expect(screen.queryByText('Save')).not.toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalledWith('/api/config', expect.anything());
});

test('submitting a valid change posts the updated config', () => {
  renderConfig();
  fetch.mockClear();

  fireEvent.change(screen.getByLabelText('Target temperature'), { target: { value: '130' } });
  fireEvent.click(screen.getByText('Save'));

  const postCall = fetch.mock.calls.find(([url]) => url === '/api/config');
  expect(postCall).toBeDefined();
  const [, opts] = postCall;
  expect(opts.method).toBe('POST');
  expect(JSON.parse(opts.body).set_temperature).toBe('130');
});
