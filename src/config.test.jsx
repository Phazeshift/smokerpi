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
  expect(screen.getByLabelText('Damper min')).toHaveValue('500');
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

test('shows the pin and interval settings as read-only, and the editable ones as editable', () => {
  renderConfig();

  ['Graph interval', 'Max CS Pin', 'Max Clock Pin', 'Max Data Pin', 'Blower pin 1', 'Blower pin 2', 'Damper pin']
    .forEach(label => expect(screen.getByLabelText(label)).toBeDisabled());
  ['Target temperature', 'Damper min', 'Damper max']
    .forEach(label => expect(screen.getByLabelText(label)).not.toBeDisabled());
  expect(screen.getByText(/edit config\.json/i)).toBeInTheDocument();
});

test.each([
  ['Target temperature', 'hot'],
  ['Damper max', '12.5'],
  ['Damper min', ''],
])('%s = "%s" shows an error next to the field and is not posted', (label, value) => {
  renderConfig();
  fetch.mockClear();

  fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByText('Save'));

  expect(screen.getByText(value === '' ? 'Enter value' : 'Enter a whole number')).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalledWith('/api/config', expect.anything());
});

test('posts only the editable settings, not the read-only ones', () => {
  renderConfig();
  fetch.mockClear();

  fireEvent.click(screen.getByText('Save'));

  const postCall = fetch.mock.calls.find(([url]) => url === '/api/config');
  expect(Object.keys(JSON.parse(postCall[1].body)).sort()).toEqual(
    ['damper_maximum', 'damper_minimum', 'set_temperature']
  );
});

test('does not show or post blower_minimum, even if the server still sends it', () => {
  // older config.json files may still contain it; it was never used by the control loop
  renderWithStore(<Config />, {
    preloadedState: { smokerpi: { graphData: [], graphIndex: 0, config: { ...fullConfig, blower_minimum: 40 } } },
  });
  fetch.mockClear();

  expect(screen.queryByLabelText('Blower minimum')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Save'));

  const postCall = fetch.mock.calls.find(([url]) => url === '/api/config');
  expect(JSON.parse(postCall[1].body)).not.toHaveProperty('blower_minimum');
});
