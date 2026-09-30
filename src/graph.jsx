import React, { Component } from 'react';
import { connect } from 'react-redux';
import * as actions from './actions/actions';
import * as selectors from './selectors/selector';
import { ResponsiveContainer, Line, LineChart,XAxis,YAxis,Tooltip,CartesianGrid,Legend } from 'recharts'

// Recharts 3 sorts tooltip and legend entries by name by default; keep them in the order
// the lines are declared in.
const SERIES_ORDER = ['t', 'b', 'd', 's'];

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
                            {/* Two independent, hidden value scales: axis 0 for temperature and
                                setpoint, axis 1 for the 0-100 blower and damper. Recharts 2+ needs
                                an axis declared for every yAxisId a Line uses. */}
                            <YAxis yAxisId={0} hide />
                            <YAxis yAxisId={1} hide />
                            <Tooltip itemSorter={item => SERIES_ORDER.indexOf(item.dataKey)} />
                            <Legend itemSorter={null} />
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