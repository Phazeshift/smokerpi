import {toastr} from "react-redux-toastr";

export const LOAD_DATA_SUCCESS = "LOAD_DATA_SUCCESS";
export const DATA_LOADED = "DATA_LOADED";
export const SEND_WEBSOCKET_MESSAGE = "SEND_WEBSOCKET_MESSAGE";
export const SOCKET_MESSAGE_RECEIVED = "SOCKET_MESSAGE_RECEIVED";

export const getTime = () => dispatch => {
    return fetch(
        '/api/time')
        .then(response => {
            if (response.ok) {
                return response.json();
            }            throw new Error(response.statusText);
        })
        .then(
            data => {
                toastr.removeByType('error');
                dispatch({type: LOAD_DATA_SUCCESS, data});
            },
            error => {
                toastr.error(`Error loading data: ${error.message}`);
            })
}

export const toggleBlower = () => {
        return (dispatch) => {		
            dispatch({ type: SEND_WEBSOCKET_MESSAGE, method: 'toggleBlower', payload: {} });		
        }	    
    }   

export const toggleAutomatic = () => {
        return (dispatch) => {		
            dispatch({ type: SEND_WEBSOCKET_MESSAGE, method: 'toggleAutomatic', payload: {} });		
        }	    
    }       

export const getState = () => {
    return (dispatch) => {		
        dispatch({ type: SEND_WEBSOCKET_MESSAGE, method: 'getState', payload: {} });		
    }
}	    

export const getAllGraph = () => {
        return (dispatch) => {		
            dispatch({ type: SEND_WEBSOCKET_MESSAGE, method: 'getAllGraph', payload: {} });		
        }
    }	    
   
