import React, { Component } from 'react';
import { connect } from 'react-redux';
import "bootswatch/dist/flatly/bootstrap.min.css"; 
import './App.css';
import { Container, Card } from 'react-bootstrap';
import Graph from './graph';
import Controls from './controls';
import StatusCard from './statuscard';

class Home extends Component {

  render() {    
    return (                    
      <Container>       
        {/* Bootstrap 4's CardDeck (removed in 5) left a gap between stacked cards
            below the sm breakpoint only; mb-3 mb-sm-0 reproduces that. */}
        <div className="mb-3 mb-sm-0">
          <StatusCard />
        </div>
        <div className="mb-3 mb-sm-0">
          <Card>
            <Card.Body>
              <Controls />
            </Card.Body>
          </Card>
        </div>
        <div className="mb-3 mb-sm-0">
          <Card>
            <Card.Body>
              <Graph />
              <div className="mt-2 text-end">
                <a href="/api/history.csv" download="smokerpi-history.csv">Download history (CSV)</a>
              </div>
            </Card.Body>
          </Card>
        </div>
      </Container>   
  )};
}

const mapStateToProps = state => ({ })

const mapDispatchToProps = dispatch => ({ })

export default connect(mapStateToProps, mapDispatchToProps)(Home);