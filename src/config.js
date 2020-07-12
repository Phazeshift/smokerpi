import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import { Container, Button, Row, Form } from 'react-bootstrap';
import { FormInput } from  './forminput.js'

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

    componentWillReceiveProps(nextProps) {                
        this.setState({ config: { ...nextProps }});        
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
        let text = JSON.stringify(this.state);
        if (!this.state.config || !this.state.config.set_temperature) { 
            return ( 
            <div>{text}</div> 
            );        
        }
        
        const {
            submitted,
            errors
          } = this.state;
      return (         
        <Container>   
            <h2>Config</h2>
            <div>{text}</div>
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
              label="Push interval"
              name="push_interval"
              type="text"
              value={this.state.config.push_interval}
              onChange={this.handleChange}
              placeholder="Enter value..."
              error={errors.push_interval}
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
            </Form>
            <Row><Button onClick={this.onSubmit}>Save</Button></Row>
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