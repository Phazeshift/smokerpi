import React, { Component } from 'react';
import { connect } from 'react-redux';
import "bootswatch/dist/flatly/bootstrap.min.css"; 
import './App.css';
import { Container, Card, CardDeck } from 'react-bootstrap';
import Graph from './graph';
import Controls from './controls';
import StatusCard from './statuscard';

class Home extends Component {

  render() {    
    return (                    
      <Container>       
        <CardDeck>
          <StatusCard />      
        </CardDeck>
        <CardDeck>
          <Card>
            <Card.Body>
              <Controls />      
            </Card.Body> 
          </Card>
        </CardDeck>
        <CardDeck>
          <Card>
            <Card.Body>                 
              <Graph />                         
            </Card.Body>
          </Card>
        </CardDeck>     
      </Container>   
  )};
}

const mapStateToProps = state => ({ })

const mapDispatchToProps = dispatch => ({ })

export default connect(mapStateToProps, mapDispatchToProps)(Home);