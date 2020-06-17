import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import MyNavBar from './NavBar';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { Container,Button, Row, Col, Jumbotron } from 'react-bootstrap';


class App extends Component {
  
  componentDidMount() {
    this.props.getState();
  }

  render() {    
    return (          
    <div>
      <MyNavBar appTitle='SmokerPi' />
      <Container fluid>
      {/* <div className="App-logo"> 
        <img src={fire} alt="Logo" />
    </div> */}    
      <Jumbotron>
        <Row>
           <Col className='d-flex justify-content-center'>
             <h1>{this.props.smoker.temperature}°C</h1>      
           </Col>
        </Row>        
      </Jumbotron>
      <Row className='d-flex align-items-end'>
      <Col xs='1'></Col>
      <Col >
        <small>Blower: {this.props.smoker.blower}</small>
      </Col>
      </Row>
      <Row>
        <Col className='d-flex justify-content-center'>
            <Button variant="light" onClick={this.props.getState}>Test getState</Button>       
            <Button variant="light" onClick={this.props.toggleBlower}>Test blower</Button>             
        </Col>
      </Row>  
      <pre className='text-black-50'>
      {
      JSON.stringify(this.props)
      }
      </pre>          
    </Container>
    </div>    
  )};
}

const mapStateToProps = state => ({
  ...state
 })

const mapDispatchToProps = dispatch => ({
  getTime: () => dispatch(actions.getTime()),
  getState: () => dispatch(actions.getState()),
  itemAdded: (data) => dispatch(actions.itemAdded(data)),
  toggleBlower: () => dispatch(actions.toggleBlower())
 })

export default connect(mapStateToProps, mapDispatchToProps)(App);