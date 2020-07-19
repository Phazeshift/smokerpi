import io from "socket.io-client"

export const socketMiddleware = (url) => {
        return store => {    
        
        let socket = io.connect(url);
        console.dir(socket);
        
        socket.on('message', (message) => {
            console.log(message);
            store.dispatch({
                type : 'SOCKET_MESSAGE_RECEIVED',
                payload : message
            });
        });

        return next => action => {            
            if(action.type === "SEND_WEBSOCKET_MESSAGE") {
                console.log(action);
                socket.emit(action.method, action.payload);
                return;
            }

            return next(action);
        }    
    }
}