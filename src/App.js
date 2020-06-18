import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import MyNavBar from './NavBar';
/* import 'bootstrap/dist/css/bootstrap.min.css'; */
import "bootswatch/dist/flatly/bootstrap.min.css"; 
import './App.css';
import { Container,Button, Row, Col, Card, CardDeck } from 'react-bootstrap';


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
    <CardDeck>
      <Card bg='light' style={{ width: '150rem' }}>
        <Card.Body className='d-flex justify-content-center'>
        <h1>{this.props.smoker.temperature}°C</h1> 
        </Card.Body>
        <Card.Footer className="text-muted">
          <small>Blower: {this.props.smoker.blower}</small>
        </Card.Footer>
      </Card> 
      </CardDeck>
      <CardDeck>
      <Card>
      <Card.Body>
      <Row>
        <Col className='d-flex justify-content-center'>
            <Button variant="light" onClick={this.props.getState}>Test getState</Button>       
            <Button variant="light" onClick={this.props.toggleBlower}>Test blower</Button>             
        </Col>
      </Row> 
      </Card.Body> 
      </Card>
      </CardDeck>
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