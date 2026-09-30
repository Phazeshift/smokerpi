import {LOAD_GRAPH_DATA_SUCCESS, LOAD_CONFIG_DATA_SUCCESS, LOAD_STATE_DATA_SUCCESS, SOCKET_MESSAGE_RECEIVED, API_ERROR, API_ERROR_DISMISSED} from "../actions/actions";

// Drops the error key (rather than setting it to null) so state without an error is unchanged.
const withoutError = ({ error, ...rest }) => rest;

export default function reducer(state = { graphData: [], graphIndex: 0 }, action) {
    switch (action.type) {
        case LOAD_GRAPH_DATA_SUCCESS: {
            var graphData = [...state.graphData];
            graphData = graphData.concat(action.data);
            var maxGraph = graphData.reduce((max, n) => n.i > max ? n.i : max, 0) + 1;

            return {
                ...withoutError(state),
                graphIndex: maxGraph,
                graphData: graphData
            }
        }
        case LOAD_CONFIG_DATA_SUCCESS: {
            return {
                ...withoutError(state),
                config: action.data
            }
        }
        case LOAD_STATE_DATA_SUCCESS: {
            return {
                ...withoutError(state),
                state: action.data
            }
        }
        case API_ERROR: {
            return {
                ...state,
                error: action.message
            }
        }
        case API_ERROR_DISMISSED: {
            return state.error === undefined ? state : withoutError(state);
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