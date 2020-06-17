import {LOAD_DATA_SUCCESS, SOCKET_MESSAGE_RECEIVED} from "../actions/actions";

export default function reducer(state = { }, action) {
    switch (action.type) {
        case LOAD_DATA_SUCCESS: {
            return {
                ...state,
                ...action.data
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