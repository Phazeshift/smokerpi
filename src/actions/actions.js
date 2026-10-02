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

// A manual control posts the opposite of what it is now, then refreshes the state.
const toggle = (url, isOn) => () => (dispatch, getState) => {
    const enabled = !isOn(getState().smokerpi.state);
    return postApi(dispatch, url, { enabled }, () => dispatch(getCurrentState()));
}

export const toggleBlower = toggle(`/api/blower`, state => state.blower === 100);
export const toggleDamper = toggle(`/api/damper`, state => state.damper === 100);
export const toggleAutomatic = toggle(`/api/pid`, state => state.pid);

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

// Fetch, turn an error response into an Error, and hand the parsed JSON to onSuccess.
// A failure of any kind becomes an API_ERROR action.
const request = (dispatch, url, options, onSuccess) => {
    return (options ? fetch(url, options) : fetch(url))
        .then(async response => {
            if (response.ok) {
                return response.json();
            }
            throw await responseError(response);
        })
        .then(
            data => {
                onSuccess(data);
            },
            error => {
                dispatch(apiError(error));
            })
}

const api = (dispatch, url, action) => {
    return request(dispatch, url, undefined, data => dispatch({type: action, data}));
}

const postApi = (dispatch, url, postData, then) => {
    return request(dispatch, url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(postData)
    }, data => then(dispatch, data));
}
