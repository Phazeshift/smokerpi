import React, { Component } from 'react';
import { connect } from 'react-redux';
import { toggleAutomatic, toggleBlower, toggleDamper, getGraphData } from './actions/actions';
import "bootswatch/dist/flatly/bootstrap.min.css"; 
import './App.css';
import { Button, ButtonGroup, Row, Col } from 'react-bootstrap';

class Controls extends Component {
    render() {    
        return (
      <Row>
        <Col className='d-flex justify-content-center'>
          <ButtonGroup>                   
            <Button variant="light" className='ml-1' onClick={this.props.toggleBlower}>Toggle Blower</Button>             
            <Button variant="light" className='ml-1' onClick={this.props.toggleDamper}>Toggle Damper</Button>  
            <Button variant="light" className='ml-1' onClick={this.props.toggleAutomatic}>Toggle Pid</Button>  
            <Button variant="light" className='ml-1' onClick={() => this.props.getGraphData()}>Update Graph</Button>           
          </ButtonGroup>
        </Col>
      </Row> )
    }
};

const actionCreators = {
    toggleAutomatic, toggleBlower, toggleDamper, getGraphData 
  };

export default connect(null, actionCreators)(Controls);