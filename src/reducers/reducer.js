import {LOAD_GRAPH_DATA_SUCCESS, LOAD_CONFIG_DATA_SUCCESS, LOAD_STATE_DATA_SUCCESS, SOCKET_MESSAGE_RECEIVED} from "../actions/actions";

export default function reducer(state = { graphData: [], graphIndex: 0 }, action) {
    switch (action.type) {
        case LOAD_GRAPH_DATA_SUCCESS: {
            var graphData = [...state.graphData];
            graphData = graphData.concat(action.data);
            var maxGraph = graphData.reduce((max, n) => n.i > max ? n.i : max, 0) + 1;

            return {
                ...state,
                graphIndex: maxGraph,
                graphData: graphData
            }
        }
        case LOAD_CONFIG_DATA_SUCCESS: {
            return {
                ...state,                
                config: action.data
            }
        }
        case LOAD_STATE_DATA_SUCCESS: {
            return {
                ...state,                
                state: action.data
            }
        }
        case SOCKET_MESSAGE_RECEIVED: {
            return {
                ...state,
                ...action.payload
            }
        }
        default: {
            return state;
        }
    }
}