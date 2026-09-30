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

test('clearing the required target temperature keeps the form; Save shows an error and does not post', () => {
  renderConfig();
  fetch.mockClear();

  fireEvent.change(screen.getByLabelText('Target temperature'), { target: { value: '' } });
  expect(screen.getByLabelText('Target temperature')).toHaveValue('');

  fireEvent.click(screen.getByText('Save'));

  expect(screen.getByText('Enter value')).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalledWith('/api/config', expect.anything());
});

test('shows a loading message, not raw component state, until the config arrives', () => {
  fetch.mockResponse(() => new Promise(() => {}));
  const { container } = renderWithStore(<Config />, {
    preloadedState: { smokerpi: { graphData: [], graphIndex: 0 } },
  });

  expect(screen.getByText(/loading/i)).toBeInTheDocument();
  expect(container).not.toHaveTextContent('submitted');
});

test('does not dump raw component state into the page', () => {
  const { container } = renderConfig();
  expect(container).not.toHaveTextContent('submitted');
  expect(container).not.toHaveTextContent('"errors"');
});

test('has no Push interval field, and posts no push_interval', () => {
  renderConfig();
  fetch.mockClear();

  expect(screen.queryByLabelText('Push interval')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Save'));

  const postCall = fetch.mock.calls.find(([url]) => url === '/api/config');
  expect(JSON.parse(postCall[1].body)).not.toHaveProperty('push_interval');
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
