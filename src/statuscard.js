import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import "bootswatch/dist/flatly/bootstrap.min.css"; 
import './App.css';
import { Card } from 'react-bootstrap';

class StatusCard extends Component {
    state = {
      timer: null  
    };
    
    componentDidMount() {
      this.props.getCurrentState();
      let timer = setInterval(() => this.props.getCurrentState(), 30000);        
      this.setState({timer});
    }
    
    componentWillUnmount(){
        clearInterval(this.state.timer)     
    }

    render() {    
        return (
            <Card bg='light'>
                <Card.Body className='d-flex justify-content-center'>
                    <h1>{this.props.temperature}°C</h1> 
                </Card.Body>
                <Card.Footer className="text-muted">
                    <small>Blower: {this.props.blower} Damper: {this.props.damper} Pid: {this.props.pid ? 'On' : 'Off'} Target: {this.props.targetTemperature}</small>
                </Card.Footer>
            </Card> 
      )
    }
};

const mapStateToProps = state => ({
    ...state.smokerpi.state
   });

const mapDispatchToProps = dispatch => ({        
    getCurrentState: () => dispatch(actions.getCurrentState()),  
   });

export default connect(mapStateToProps, mapDispatchToProps)(StatusCard);