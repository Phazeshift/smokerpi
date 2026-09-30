import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import { Container, Button, Form } from 'react-bootstrap';
import { FormInput } from './forminput'

class Config extends Component {    
    state = {        
        errors: {},
        submitted: false
      };

    handleChange = event => {
        const { config } = this.state;        
        config[event.target.name] = event.target.value;
        this.setState({ config });
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
        const {
          config: { set_temperature }
        } = this.state;
        let err = {};
    
        if (!set_temperature) {
          err.set_temperature = "Enter value";
        }
        
        this.setState({ errors: err }, () => {
          if (Object.getOwnPropertyNames(this.state.errors).length === 0) {
            this.setState({ submitted: true });            
            this.props.updateConfig(this.state.config);    
          }
        });
      };

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
        
        const {            
            errors
          } = this.state;
      return (         
        <Container>   
            <h2>Config</h2>
            <Form>
            <FormInput
              label="Target temperature"
              name="set_temperature"
              type="text"
              value={this.state.config.set_temperature}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.set_temperature}
              required
              className="input"
             />
             <FormInput
              label="Blower minimum"
              name="blower_minimum"
              type="text"
              value={this.state.config.blower_minimum}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.blower_minimum}
              required
              className="input"
            />
            <FormInput
              label="Graph interval"
              name="graph_interval"
              type="text"
              value={this.state.config.graph_interval}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.graph_interval}
              required
              className="input"
            />
            <FormInput
              label="Max CS Pin"
              name="cs_pin"
              type="text"
              value={this.state.config.cs_pin}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.cs_pin}
              required
              className="input"
            />
            <FormInput
              label="Max Clock Pin"
              name="clock_pin"
              type="text"
              value={this.state.config.clock_pin}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.clock_pin}
              required
              className="input"
            />
            <FormInput
              label="Max Data Pin"
              name="data_pin"
              type="text"
              value={this.state.config.data_pin}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.data_pin}
              required
              className="input"
            />
            <FormInput
              label="Blower pin 1"
              name="blower_pin1"
              type="text"
              value={this.state.config.blower_pin1}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.blower_pin1}
              required
              className="input"
            />
             <FormInput
              label="Blower pin 2"
              name="blower_pin2"
              type="text"
              value={this.state.config.blower_pin2}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.blower_pin2}
              required
              className="input"
            />
             <FormInput
              label="Damper pin"
              name="damper_pin"
              type="text"
              value={this.state.config.damper_pin}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.damper_pin}
              required
              className="input"
            />
            <FormInput
              label="Damper min"
              name="damper_minimum"
              type="text"
              value={this.state.config.damper_minimum}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.damper_minimum}
              required
              className="input"
            />
            <FormInput
              label="Damper max"
              name="damper_maximum"
              type="text"
              value={this.state.config.damper_maximum}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.damper_maximum}
              required
              className="input"
            />
            </Form>
            <div className="mb-3"><Button onClick={this.onSubmit}>Save</Button></div>
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