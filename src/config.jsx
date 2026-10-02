import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import * as actions from './actions/actions';
import { Container, Button, Form } from 'react-bootstrap';
import { FormInput } from './forminput'

// The form is built from `fields` in the GET /api/config response (see describeFields in
// api/smokerpi/config.py): the server says which settings to show, their labels and how
// each is edited and checked. kind is
//   whole  a required whole number    gain  a number, 0 or more    bool  a checkbox
//   null   read-only: the API ignores it because it needs a restart (edit config.json on the Pi)
const fieldsIn = (config, kind) => (config.fields || []).filter(field => field.kind === kind);

const isWholeNumber = value => /^\s*-?\d+\s*$/.test(String(value));
const isNumber = value => /^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$/.test(String(value));

// Ranges are checked by the server, which explains any rejection in the error banner.
const validate = config => {
  const errors = {};
  [...fieldsIn(config, 'whole'), ...fieldsIn(config, 'gain')].forEach(({ name, kind }) => {
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
      [...fieldsIn(config, 'whole'), ...fieldsIn(config, 'gain'), ...fieldsIn(config, 'bool')].forEach(({ name, kind }) => {
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
        {fieldsIn(config, 'bool').map(({ name, label, help }) => (
          <Form.Group className="mb-3" key={name}>
            <Form.Check
              type="checkbox"
              id={name}
              name={name}
              label={label}
              checked={!!config[name]}
              onChange={handleChange}
            />
            {help && <Form.Text className="text-muted">{help}</Form.Text>}
          </Form.Group>
        ))}
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
