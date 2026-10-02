import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import * as actions from './actions/actions';
import { Container, Button, Form } from 'react-bootstrap';
import { FormInput } from './forminput'

// Every setting the page knows how to show; see FIELDS in api/smokerpi/config.py for the
// server side. The server's keys decide what is on the page: a whole number is always
// shown (the server needs it), every other field only if the server sent it, and a key
// not listed here is not shown. kind says how it is edited and checked:
//   whole  a required whole number    gain  a number, 0 or more    bool  a checkbox
//   null   read-only: the API ignores it because it needs a restart (edit config.json on the Pi)
const FIELDS = [
  { name: 'set_temperature', label: 'Target temperature', kind: 'whole' },
  { name: 'damper_minimum', label: 'Damper min', kind: 'whole' },
  { name: 'damper_maximum', label: 'Damper max', kind: 'whole' },
  { name: 'damper_invert', label: 'Invert damper', kind: 'bool' },
  { name: 'pid_kp', label: 'PID Kp (proportional)', kind: 'gain' },
  { name: 'pid_ki', label: 'PID Ki (integral, per second)', kind: 'gain' },
  { name: 'pid_kd', label: 'PID Kd (derivative)', kind: 'gain' },
  { name: 'graph_interval', label: 'Graph interval', kind: null },
  { name: 'cs_pin', label: 'Max CS Pin', kind: null },
  { name: 'clock_pin', label: 'Max Clock Pin', kind: null },
  { name: 'data_pin', label: 'Max Data Pin', kind: null },
  { name: 'blower_pin1', label: 'Blower pin 1', kind: null },
  { name: 'blower_pin2', label: 'Blower pin 2', kind: null },
  { name: 'damper_pin', label: 'Damper pin', kind: null },
];

// The fields to show for this config, of the given kinds.
const fieldsIn = (config, ...kinds) =>
  FIELDS.filter(({ name, kind }) => kinds.includes(kind) && (kind === 'whole' || config[name] !== undefined));

const isWholeNumber = value => /^\s*-?\d+\s*$/.test(String(value));
const isNumber = value => /^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$/.test(String(value));

// Ranges are checked by the server, which explains any rejection in the error banner.
const validate = config => {
  const errors = {};
  fieldsIn(config, 'whole', 'gain').forEach(({ name, kind }) => {
    const value = config[name];
    if (value === undefined || value === null || String(value).trim() === '') {
      errors[name] = 'Enter value';
    } else if (kind === 'whole' && !isWholeNumber(value)) {
      errors[name] = 'Enter a whole number';
    } else if (kind === 'gain' && !isNumber(value)) {
      errors[name] = 'Enter a number';
    } else if (kind === 'gain' && Number(value) < 0) {
      errors[name] = 'Enter a number, 0 or more';
    }
  });
  return errors;
};

const Config = () => {
  const dispatch = useDispatch();
  const stored = useSelector(state => state.smokerpi.config);
  // The editable copy of the stored config, re-synced whenever the store's config changes
  // (e.g. after getConfig completes).
  const [config, setConfig] = useState(() => (stored ? { ...stored } : undefined));
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setConfig(stored ? { ...stored } : undefined);
  }, [stored]);

  useEffect(() => {
    dispatch(actions.getConfig());
  }, [dispatch]);

  const handleChange = event => {
    const { name, value, type, checked } = event.target;
    const newValue = type === 'checkbox' ? checked : value;
    setConfig(current => ({ ...current, [name]: newValue }));
  };

  const onSubmit = () => {
    const newErrors = validate(config);
    setErrors(newErrors);
    if (Object.keys(newErrors).length === 0) {
      const editable = {};
      fieldsIn(config, 'whole', 'gain', 'bool').forEach(({ name, kind }) => {
        editable[name] = kind === 'bool' ? !!config[name] : config[name];
      });
      dispatch(actions.updateConfig(editable));
    }
  };

  const renderFields = (fields, extraProps) => fields.map(({ name, label }) => (
    <FormInput
      key={name}
      label={label}
      name={name}
      value={config[name]}
      onChange={handleChange}
      placeholder="Enter value..."
      error={errors[name]}
      {...extraProps}
    />
  ));

  // Show a placeholder until the config has been fetched. This must test whether
  // it has loaded, not whether a field is non-empty: clearing a field would
  // otherwise replace the whole form.
  if (!config || config.set_temperature === undefined) {
    return (
      <Container>
        <p>Loading configuration...</p>
      </Container>
    );
  }

  return (
    <Container>
      <h2>Config</h2>
      <Form>
        {renderFields(fieldsIn(config, 'whole'))}
        {fieldsIn(config, 'bool').length > 0 && (
          <Form.Group className="mb-3">
            <Form.Check
              type="checkbox"
              id="damper_invert"
              name="damper_invert"
              label="Invert damper"
              checked={!!config.damper_invert}
              onChange={handleChange}
            />
            <Form.Text className="text-muted">
              Tick this if your damper opens at the smaller pulse width (Damper min) instead of the
              larger one. Saving moves the damper to match.
            </Form.Text>
          </Form.Group>
        )}
        {fieldsIn(config, 'gain').length > 0 && (
          <>
            <h5 className="mt-4">PID tuning</h5>
            <p className="text-muted">
              Applied immediately. The loop runs about every 11 seconds, so a Ki of 0.1 is a very fast
              integral. Larger Kp and much smaller Ki suit a smoker: Kp 5, Ki 0.005, Kd 0 is a starting
              point to try, not a tested setting.
            </p>
            {renderFields(fieldsIn(config, 'gain'))}
          </>
        )}
      </Form>
      <div className="mb-3"><Button onClick={onSubmit}>Save</Button></div>

      <h5 className="mt-4">Hardware and timing</h5>
      <p className="text-muted">
        These can't be changed here. Edit config.json on the Pi and restart SmokerPi to change them.
      </p>
      <Form>{renderFields(fieldsIn(config, null), { disabled: true })}</Form>
    </Container>
  );
};

export default Config;
