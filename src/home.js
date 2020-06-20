import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import "bootswatch/dist/flatly/bootstrap.min.css"; 
import './App.css';
import { Container,Button, ButtonGroup, Row, Col, Card, CardDeck } from 'react-bootstrap';
import { ResponsiveContainer, Line, LineChart,XAxis,Tooltip,CartesianGrid,Legend } from 'recharts'

class Home extends Component {

  componentDidMount() {
    this.props.getState();
    this.props.getAllGraph();
  }

  render() {    
    return (          
    <div>      
      <Container>       
    <CardDeck>
      <Card bg='light'>
        <Card.Body className='d-flex justify-content-center'>
        <h1>{this.props.smoker.temperature}°C</h1> 
        </Card.Body>
        <Card.Footer className="text-muted">
  <small>Blower: {this.props.smoker.blower} Pid: {this.props.smoker.pid ? 'On' : 'Off'} Target: {this.props.smoker.targetTemperature}</small>
        </Card.Footer>
      </Card> 
      </CardDeck>
      <CardDeck>
      <Card>
      <Card.Body>
      <Row>
        <Col className='d-flex justify-content-center'>
          <ButtonGroup>
            <Button variant="light" className='ml-1' onClick={this.props.getState}>Test getState</Button>       
            <Button variant="light" className='ml-1' onClick={this.props.toggleBlower}>Test blower</Button>             
            <Button variant="light" className='ml-1' onClick={this.props.toggleAutomatic}>Test pid</Button>  
            <Button variant="light" className='ml-1' onClick={this.props.getAllGraph}>Test graph</Button> 
          </ButtonGroup>
        </Col>
      </Row> 
      </Card.Body> 
      </Card>
      </CardDeck>
      <CardDeck>
      <Card>
      <Card.Body><div style={{
  paddingBottom: '56.25%', /* 16:9 */
  position: 'relative',
  height: 0
}} >
  <div style={{
    position: 'absolute',
    top: '0',
    left: '0',
    width: '100%',
    height: '100%'
  }}>
      <ResponsiveContainer>
      <LineChart   
  data={this.props.smoker.graphData}
  margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
>
  <XAxis dataKey="x" />  
  <Tooltip />
  <Legend />
  <CartesianGrid stroke="#f5f5f5" />  
  <Line type="monotone" dataKey="t" stroke="#ff7300" dot={false} yAxisId={0} />
  <Line type="monotone" dataKey="b" stroke="#82ca9d" dot={false} yAxisId={1} />
  <Line type="monotone" dataKey="s" stroke="#8884d8" dot={false} yAxisId={0} />
  </LineChart>  
      </ResponsiveContainer> 
      </div>
      </div>      
</Card.Body>
      </Card>
      </CardDeck>     
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
  getAllGraph: () => dispatch(actions.getAllGraph()),  
  toggleBlower: () => dispatch(actions.toggleBlower()),
  toggleAutomatic: () => dispatch(actions.toggleAutomatic())
 })

export default connect(mapStateToProps, mapDispatchToProps)(Home);