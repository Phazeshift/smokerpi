import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithStore } from './testUtils';
import Config from './config';

// What the server sends in `fields` (describeFields in api/smokerpi/config.py), for the keys a
// config has.
const FIELD_TABLE = [
  { name: 'cs_pin', label: 'Max CS Pin', kind: null },
  { name: 'clock_pin', label: 'Max Clock Pin', kind: null },
  { name: 'data_pin', label: 'Max Data Pin', kind: null },
  { name: 'blower_pin1', label: 'Blower pin 1', kind: null },
  { name: 'blower_pin2', label: 'Blower pin 2', kind: null },
  { name: 'damper_pin', label: 'Damper pin', kind: null },
  { name: 'set_temperature', label: 'Target temperature', kind: 'whole' },
  { name: 'graph_interval', label: 'Graph interval', kind: null },
  { name: 'pid_kp', label: 'PID Kp (proportional)', kind: 'gain' },
  { name: 'pid_ki', label: 'PID Ki (integral, per second)', kind: 'gain' },
  { name: 'pid_kd', label: 'PID Kd (derivative)', kind: 'gain' },
  {
    name: 'damper_invert', label: 'Invert damper', kind: 'bool',
    help: 'Tick this if your damper opens at the smaller pulse width (Damper min) instead of the larger one. Saving moves the damper to match.',
  },
  { name: 'damper_minimum', label: 'Damper min', kind: 'whole' },
  { name: 'damper_maximum', label: 'Damper max', kind: 'whole' },
  { name: 'oled_enabled', label: 'OLED display', kind: null },
  { name: 'oled_driver', label: 'OLED driver', kind: null, help: 'sh1106, ssd1306 or ssd1309.' },
  { name: 'oled_address', label: 'OLED I2C address', kind: null },
];
const withFields = config => ({ ...config, fields: FIELD_TABLE.filter(({ name }) => name in config) });

const baseConfig = {
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
const fullConfig = withFields(baseConfig);

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

test('shows the OLED settings as read-only, with their values', () => {
  const state = { ...baseConfig, oled_enabled: true, oled_driver: 'sh1106', oled_address: '0x3c' };
  fetch.mockResponse(JSON.stringify(withFields(state)));
  renderWithStore(<Config />);

  return screen.findByLabelText('OLED driver').then(driver => {
    expect(driver).toBeDisabled();
    expect(driver).toHaveValue('sh1106');
    expect(screen.getByLabelText('OLED I2C address')).toBeDisabled();
    expect(screen.getByLabelText('OLED I2C address')).toHaveValue('0x3c');
    expect(screen.getByLabelText('OLED display')).toBeDisabled();
    expect(screen.getByLabelText('OLED display')).toHaveValue('true');
  });
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
    preloadedState: { smokerpi: { graphData: [], graphIndex: 0, config: withFields({ ...baseConfig, blower_minimum: 40 }) } },
  });
  fetch.mockClear();

  expect(screen.queryByLabelText('Blower minimum')).not.toBeInTheDocument();
  fireEvent.click(screen.getByText('Save'));

  const postCall = fetch.mock.calls.find(([url]) => url === '/api/config');
  expect(JSON.parse(postCall[1].body)).not.toHaveProperty('blower_minimum');
});

describe('PID gains', () => {
  const withGains = withFields({ ...baseConfig, pid_kp: 1, pid_ki: 0.1, pid_kd: 0.05 });
  const renderWithGains = () => renderWithStore(<Config />, {
    preloadedState: { smokerpi: { graphData: [], graphIndex: 0, config: withGains } },
  });

  beforeEach(() => {
    fetch.mockResponse(JSON.stringify(withGains));
  });

  test('shows the gains as editable fields, filled in from the config', () => {
    renderWithGains();

    expect(screen.getByLabelText('PID Kp (proportional)')).toHaveValue('1');
    expect(screen.getByLabelText('PID Ki (integral, per second)')).toHaveValue('0.1');
    expect(screen.getByLabelText('PID Kd (derivative)')).toHaveValue('0.05');
    expect(screen.getByLabelText('PID Ki (integral, per second)')).not.toBeDisabled();
  });

  test('posts the gains, as entered, with the other settings', () => {
    renderWithGains();
    fetch.mockClear();

    fireEvent.change(screen.getByLabelText('PID Kp (proportional)'), { target: { value: '5' } });
    fireEvent.change(screen.getByLabelText('PID Ki (integral, per second)'), { target: { value: '0.005' } });
    fireEvent.click(screen.getByText('Save'));

    const body = JSON.parse(fetch.mock.calls.find(([url]) => url === '/api/config')[1].body);
    expect(body).toMatchObject({ pid_kp: '5', pid_ki: '0.005', pid_kd: 0.05, set_temperature: 105 });
  });

  test.each([
    ['PID Kp (proportional)', 'fast', 'Enter a number'],
    ['PID Ki (integral, per second)', '-1', 'Enter a number, 0 or more'],
    ['PID Kd (derivative)', '', 'Enter value'],
  ])('%s = "%s" shows an error and is not posted', (label, value, message) => {
    renderWithGains();
    fetch.mockClear();

    fireEvent.change(screen.getByLabelText(label), { target: { value } });
    fireEvent.click(screen.getByText('Save'));

    expect(screen.getByText(message)).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith('/api/config', expect.anything());
  });

  test('accepts decimals and zero', () => {
    renderWithGains();
    fetch.mockClear();

    fireEvent.change(screen.getByLabelText('PID Ki (integral, per second)'), { target: { value: '0' } });
    fireEvent.change(screen.getByLabelText('PID Kp (proportional)'), { target: { value: '2.5' } });
    fireEvent.click(screen.getByText('Save'));

    expect(fetch).toHaveBeenCalledWith('/api/config', expect.anything());
  });

  test('shows no gain fields, and posts none, when the server does not send them', () => {
    // a server older than the gains setting
    fetch.mockResponse(JSON.stringify(fullConfig));
    renderConfig();
    fetch.mockClear();

    expect(screen.queryByLabelText('PID Kp (proportional)')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Save'));

    const body = JSON.parse(fetch.mock.calls.find(([url]) => url === '/api/config')[1].body);
    expect(Object.keys(body).some(key => key.startsWith('pid_'))).toBe(false);
  });
});

describe('Damper invert', () => {
  const withInvert = withFields({ ...baseConfig, damper_invert: false });

  beforeEach(() => {
    fetch.mockResponse(JSON.stringify(withInvert));
  });

  const renderWithInvert = (config = withInvert) => renderWithStore(<Config />, {
    preloadedState: { smokerpi: { graphData: [], graphIndex: 0, config } },
  });

  test('shows an unticked checkbox when the damper is not inverted', () => {
    renderWithInvert();
    const box = screen.getByLabelText(/Invert damper/);
    expect(box).toHaveAttribute('type', 'checkbox');
    expect(box).not.toBeChecked();
    expect(box).not.toBeDisabled();
  });

  test('shows it ticked when the damper is inverted', () => {
    fetch.mockResponse(JSON.stringify({ ...withInvert, damper_invert: true }));
    renderWithInvert({ ...withInvert, damper_invert: true });
    expect(screen.getByLabelText(/Invert damper/)).toBeChecked();
  });

  test('ticking it posts damper_invert as a boolean true', () => {
    renderWithInvert();
    fetch.mockClear();

    fireEvent.click(screen.getByLabelText(/Invert damper/));
    fireEvent.click(screen.getByText('Save'));

    const body = JSON.parse(fetch.mock.calls.find(([url]) => url === '/api/config')[1].body);
    expect(body.damper_invert).toBe(true);
  });

  test('posts false when it is left unticked', () => {
    renderWithInvert();
    fetch.mockClear();

    fireEvent.click(screen.getByText('Save'));

    const body = JSON.parse(fetch.mock.calls.find(([url]) => url === '/api/config')[1].body);
    expect(body.damper_invert).toBe(false);
  });

  test('explains what it does', () => {
    renderWithInvert();
    expect(screen.getByText(/smaller pulse width/i)).toBeInTheDocument();
  });

  test('is not shown, and not posted, when the server does not send it', () => {
    fetch.mockResponse(JSON.stringify(fullConfig));
    renderConfig();
    fetch.mockClear();

    expect(screen.queryByLabelText(/Invert damper/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Save'));

    const body = JSON.parse(fetch.mock.calls.find(([url]) => url === '/api/config')[1].body);
    expect(body).not.toHaveProperty('damper_invert');
  });
});
