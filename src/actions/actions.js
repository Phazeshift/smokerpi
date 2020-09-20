import {toastr} from "react-redux-toastr";

export const LOAD_DATA_SUCCESS = "LOAD_DATA_SUCCESS";
export const LOAD_GRAPH_DATA_SUCCESS = "LOAD_GRAPH_DATA_SUCCESS";
export const LOAD_CONFIG_DATA_SUCCESS = "LOAD_CONFIG_DATA_SUCCESS";
export const LOAD_STATE_DATA_SUCCESS = "LOAD_STATE_DATA_SUCCESS";
export const DATA_LOADED = "DATA_LOADED";
export const SEND_WEBSOCKET_MESSAGE = "SEND_WEBSOCKET_MESSAGE";
export const SOCKET_MESSAGE_RECEIVED = "SOCKET_MESSAGE_RECEIVED";

export const getGraphData = () => (dispatch, getState) => {
    let from = getState().smokerpi.graphIndex;
    return api(dispatch, `/api/graph?from=${from}`, LOAD_GRAPH_DATA_SUCCESS)
}

export const getConfig = () => (dispatch) => {    
    return api(dispatch, `/api/config`, LOAD_CONFIG_DATA_SUCCESS);
    }

export const updateConfig = (config) => (dispatch) => {    
    return postApi(dispatch, `/api/config`, config, () => dispatch(getConfig()));
    }    

export const getCurrentState = () => (dispatch) => {    
    return api(dispatch, `/api/state`, LOAD_STATE_DATA_SUCCESS);
    }

export const toggleBlower = () => (dispatch, getState) => {    
    let enabled = getState().smokerpi.state.blower;
    return postApi(dispatch, `/api/blower`, { enabled: enabled !== 100 }, () => dispatch(getCurrentState()));
    }

export const toggleDamper = () => (dispatch, getState) => {    
    let enabled = getState().smokerpi.state.damper;
    return postApi(dispatch, `/api/damper`, { enabled: enabled !== 100 }, () => dispatch(getCurrentState()));
    }

export const toggleAutomatic = () => (dispatch, getState) => {    
    let enabled = getState().smokerpi.state.pid;
    return postApi(dispatch, `/api/pid`, { enabled: !enabled }, () => dispatch(getCurrentState()));
    }

const api = (dispatch, url, action) => {       
    return fetch(url)
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error(response.statusText);
        })
        .then(
            data => {
                toastr.removeByType('error');
                dispatch({type: action, data});
            },
            error => {
                toastr.error(`Error calling api: ${error.message}`);
            })
    }

const postApi = (dispatch, url, postData, then) => {       
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postData) 
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error(response.statusText);
        })
        .then(
            data => {
                toastr.removeByType('error');
                then(dispatch, data);
            },
            error => {
                toastr.error(`Error calling api: ${error.message}`);
            })
    }    
   
