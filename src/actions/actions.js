export const LOAD_GRAPH_DATA_SUCCESS = "LOAD_GRAPH_DATA_SUCCESS";
export const LOAD_CONFIG_DATA_SUCCESS = "LOAD_CONFIG_DATA_SUCCESS";
export const LOAD_STATE_DATA_SUCCESS = "LOAD_STATE_DATA_SUCCESS";
export const API_ERROR = "API_ERROR";
export const API_ERROR_DISMISSED = "API_ERROR_DISMISSED";

export const dismissApiError = () => ({ type: API_ERROR_DISMISSED });

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

// Prefer the message the server sent ({"error": "..."}) over the bare HTTP status text.
const responseError = async response => {
    let message = response.statusText;
    try {
        const body = await response.json();
        if (body && body.error) {
            message = body.error;
        }
    } catch (e) {
        // not JSON; keep the status text
    }
    return new Error(message);
};

const apiError = error => ({ type: API_ERROR, message: `Error calling api: ${error.message}` });

const api = (dispatch, url, action) => {       
    return fetch(url)
        .then(async response => {
            if (response.ok) {
                return response.json();
            }
            throw await responseError(response);
        })
        .then(
            data => {
                dispatch({type: action, data});
            },
            error => {
                dispatch(apiError(error));
            })
    }

const postApi = (dispatch, url, postData, then) => {       
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postData) 
        })
        .then(async response => {
            if (response.ok) {
                return response.json();
            }
            throw await responseError(response);
        })
        .then(
            data => {
                then(dispatch, data);
            },
            error => {
                dispatch(apiError(error));
            })
    }    
   
