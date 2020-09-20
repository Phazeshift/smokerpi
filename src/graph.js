import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import * as selectors from './selectors/selector';
import { ResponsiveContainer, Line, LineChart,XAxis,Tooltip,CartesianGrid,Legend } from 'recharts'

class Graph extends Component {

    state = {
      timer: null  
    };
  
    componentDidMount() {
      this.props.getGraphData();
      let timer = setInterval(() => this.props.getGraphData(), 30000);        
      this.setState({timer});
    }
  
    componentWillUnmount(){
      clearInterval(this.state.timer)     
    }
     
    render() {    
        return (
            <div style={{
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
                            data={this.props.graphData}
                            margin={{ top: 5, right: 20, left: 10, bottom: 5 }} >
                            <XAxis dataKey="x" />  
                            <Tooltip />
                            <Legend />
                            <CartesianGrid stroke="#f5f5f5" />  
                            <Line type="monotone" dataKey="t" stroke="#ff6666" dot={false} yAxisId={0} />
                            <Line type="monotone" dataKey="b" stroke="#82ca9d" dot={false} yAxisId={1} />
                            <Line type="monotone" dataKey="d" stroke="#80b3ff" dot={false} yAxisId={1} />
                            <Line type="monotone" dataKey="s" stroke="#c7c5ed" dot={false} yAxisId={0} />
                        </LineChart> 
                    </ResponsiveContainer>  
                </div>
            </div>   )};
}

const mapStateToProps = state => ({
    graphData: selectors.getGraphData(state)
   });
  
const mapDispatchToProps = dispatch => ({        
    getGraphData: () => dispatch(actions.getGraphData()),  
    });
 
export default connect(mapStateToProps, mapDispatchToProps)(Graph);