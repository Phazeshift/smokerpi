import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import { Container, Button, Form } from 'react-bootstrap';
import { FormInput } from './forminput'

// The settings the API accepts (see EDITABLE_FIELDS in api/smokerpi/config.py).
const EDITABLE_FIELDS = [
  { name: 'set_temperature', label: 'Target temperature' },
  { name: 'damper_minimum', label: 'Damper min' },
  { name: 'damper_maximum', label: 'Damper max' },
];

// The PID gains (see PID_FIELDS in api/smokerpi/config.py). Only shown and posted when the
// server sends them, so the page still works against a server that does not know them.
const PID_FIELDS = [
  { name: 'pid_kp', label: 'PID Kp (proportional)' },
  { name: 'pid_ki', label: 'PID Ki (integral, per second)' },
  { name: 'pid_kd', label: 'PID Kd (derivative)' },
];

const pidFieldsIn = config => PID_FIELDS.filter(({ name }) => config[name] !== undefined);

// Shown for information only: the API ignores these, because they need a restart to take
// effect. They live in config.json on the Pi.
const READ_ONLY_FIELDS = [
  { name: 'graph_interval', label: 'Graph interval' },
  { name: 'cs_pin', label: 'Max CS Pin' },
  { name: 'clock_pin', label: 'Max Clock Pin' },
  { name: 'data_pin', label: 'Max Data Pin' },
  { name: 'blower_pin1', label: 'Blower pin 1' },
  { name: 'blower_pin2', label: 'Blower pin 2' },
  { name: 'damper_pin', label: 'Damper pin' },
];

const isWholeNumber = value => /^\s*-?\d+\s*$/.test(String(value));
const isNumber = value => /^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$/.test(String(value));

// Ranges are checked by the server, which explains any rejection in the error banner.
const validate = config => {
  const errors = {};
  EDITABLE_FIELDS.forEach(({ name }) => {
    const value = config[name];
    if (value === undefined || value === null || String(value).trim() === '') {
      errors[name] = 'Enter value';
    } else if (!isWholeNumber(value)) {
      errors[name] = 'Enter a whole number';
    }
  });
  pidFieldsIn(config).forEach(({ name }) => {
    const value = config[name];
    if (value === null || String(value).trim() === '') {
      errors[name] = 'Enter value';
    } else if (!isNumber(value)) {
      errors[name] = 'Enter a number';
    } else if (Number(value) < 0) {
      errors[name] = 'Enter a number, 0 or more';
    }
  });
  return errors;
};

class Config extends Component {
    state = {
        errors: {}
      };

    handleChange = event => {
        const { name, value } = event.target;
        this.setState(({ config }) => ({ config: { ...config, [name]: value } }));
      };

    componentDidMount() {
      this.setState({ config: { ...this.props }});
      this.props.getConfig();
    }

    // Re-sync the editable copy when the connected props change (e.g. after getConfig
    // completes). Compare prop values, not the props object: componentDidUpdate also
    // runs after our own setState, and in React 19 a class component gets a fresh props
    // object on every render (react-redux passes a ref prop, which React strips by
    // copying), so an identity check would loop forever.
    componentDidUpdate(prevProps) {
        const keys = new Set([...Object.keys(prevProps), ...Object.keys(this.props)]);
        if ([...keys].some(key => prevProps[key] !== this.props[key])) {
            this.setState({ config: { ...this.props }});
        }
    }

    onSubmit = () => {
        const { config } = this.state;
        const errors = validate(config);
        this.setState({ errors });
        if (Object.keys(errors).length === 0) {
          const editable = {};
          EDITABLE_FIELDS.forEach(({ name }) => { editable[name] = config[name]; });
          pidFieldsIn(config).forEach(({ name }) => { editable[name] = config[name]; });
          this.props.updateConfig(editable);
        }
      };

    renderFields(fields, extraProps) {
        const { config, errors } = this.state;
        return fields.map(({ name, label }) => (
          <FormInput
            key={name}
            label={label}
            name={name}
            value={config[name]}
            onChange={this.handleChange}
            placeholder="Enter value..."
            error={errors[name]}
            {...extraProps}
          />
        ));
      }

    render() {
        // Show a placeholder until the config has been fetched. This must test whether
        // it has loaded, not whether a field is non-empty: clearing a field would
        // otherwise replace the whole form.
        if (!this.state.config || this.state.config.set_temperature === undefined) {
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
              {this.renderFields(EDITABLE_FIELDS)}
              {pidFieldsIn(this.state.config).length > 0 && (
                <>
                  <h5 className="mt-4">PID tuning</h5>
                  <p className="text-muted">
                    Applied immediately. The loop runs about every 11 seconds, so a Ki of 0.1 is a very fast
                    integral. Larger Kp and much smaller Ki suit a smoker: Kp 5, Ki 0.005, Kd 0 is a starting
                    point to try, not a tested setting.
                  </p>
                  {this.renderFields(pidFieldsIn(this.state.config))}
                </>
              )}
            </Form>
            <div className="mb-3"><Button onClick={this.onSubmit}>Save</Button></div>

            <h5 className="mt-4">Hardware and timing</h5>
            <p className="text-muted">
              These can't be changed here. Edit config.json on the Pi and restart SmokerPi to change them.
            </p>
            <Form>{this.renderFields(READ_ONLY_FIELDS, { disabled: true })}</Form>
          </Container>
        );
    }
}

const mapStateToProps = state => ({
  ...state.smokerpi.config
 })

const mapDispatchToProps = dispatch => ({
  getConfig: () => dispatch(actions.getConfig()),
  updateConfig: (config) => dispatch(actions.updateConfig(config)),
 })

export default connect(mapStateToProps, mapDispatchToProps)(Config);
