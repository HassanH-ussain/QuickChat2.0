import socketio
import asyncio
import time
#from mywebapp import app <--- ONLY FOR CONNECTING ANOTHER WEB FRAMEWORK(ex:`APIs)
from socketio.exceptions import ConnectionRefusedError

# standard Python
sio = socketio.AsyncSimpleClient()

async def main():
    await sio.connect('http://local:5000', transports=['websocket'])

    print('my cilent sid', sio.sid)

    print ('my transport is', sio.transport)

    app = socketio.WSGIApp(sio)

    #Listening to events
    @sio.event 
    async def my_event(sid, data):
        pass

    sio.event 
    async def connect(sid, environ, auth):
        user_name = f"User_{sid[:6]}"

        await sio.emit('user_joined', {
            'message': f'{user_name} joined the chat!',
            'user': user_name,
            'timestamp': time.time()
        })
    
    sio.event
    async def disconnect(sid, reason):
        if reason == 'client_disconnect':
            print('the client disconnected')
        elif reason == 'server_disconnect':
            print('the server disconnected the client')
        else:
            print('disconnect reason:', reason)
    #Catching events
    sio.on('*')
    async def any_event(event, sid, data):
        print("Found event", event)