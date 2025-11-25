from aiohttp import web
import socketio
import time

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

# Track room members: {'room_name': {sid1, sid2, ...}}
room_members = {}

async def index(request):
    """Serve the client-side application."""
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')

@sio.event
async def connect(sid, environ, auth):
    """Handle new connection - auto-join general room"""
    # Get username
    username = auth.get('username', f'Guest_{sid[:6]}') if auth else f'Guest_{sid[:6]}'
    
    # Save to session
    await sio.save_session(sid, {'username': username})
    
    # Auto-join general room
    await sio.enter_room(sid, 'general')
    
    # Track membership
    if 'general' not in room_members:
        room_members['general'] = set()
    room_members['general'].add(sid)
    
    # Get all usernames in general room
    usernames_in_room = []
    for user_sid in room_members['general']:
        user_session = await sio.get_session(user_sid)
        usernames_in_room.append(user_session.get('username', 'Unknown'))
    
    print(f"✅ {username} connected and joined 'general' ({len(usernames_in_room)} users)")
    
    # Tell others someone joined (but not the person who just joined)
    await sio.emit('user_joined', {
        'username': username,
        'message': f'{username} joined the chat'
    }, room='general', skip_sid=sid)
    
    # Send updated user list to everyone
    await sio.emit('user_list', {
        'users': usernames_in_room,
        'count': len(usernames_in_room),
        'room': 'general'
    }, room='general')

@sio.event
async def send_message(sid, data):
    """Handle chat message - broadcast to room"""
    # Get username from session
    session = await sio.get_session(sid)
    username = session.get('username', 'Unknown')
    
    message_text = data.get('text')
    room = data.get('room', 'general')
    
    if not message_text:
        await sio.emit('error', {'message': 'Message text required'}, to=sid)
        return
    
    print(f"💬 [{room}] {username}: {message_text}")
    
    # Broadcast to everyone in the room (including sender)
    await sio.emit('new_message', {
        'username': username,
        'text': message_text,
        'room': room,
        'timestamp': time.time()
    }, room=room)

@sio.event
async def join_room_event(sid, data):
    """Let user join a specific room"""
    room_name = data.get('room')
    
    if not room_name:
        await sio.emit('error', {'message': 'Room name required'}, to=sid)
        return
    
    session = await sio.get_session(sid)
    username = session.get('username', 'Unknown')
    
    # Join the room
    await sio.enter_room(sid, room_name)
    
    # Track membership
    if room_name not in room_members:
        room_members[room_name] = set()
    room_members[room_name].add(sid)
    
    # Get usernames in this room
    usernames_in_room = []
    for user_sid in room_members[room_name]:
        user_session = await sio.get_session(user_sid)
        usernames_in_room.append(user_session.get('username', 'Unknown'))
    
    print(f"🚪 {username} joined room '{room_name}' ({len(usernames_in_room)} users)")
    
    # Notify room members
    await sio.emit('user_joined_room', {
        'username': username,
        'room': room_name,
        'message': f'{username} joined {room_name}'
    }, room=room_name, skip_sid=sid)
    
    # Confirm to user and send room info
    await sio.emit('room_joined', {
        'room': room_name,
        'users': usernames_in_room,
        'count': len(usernames_in_room),
        'message': f'You joined {room_name}'
    }, to=sid)

@sio.event
async def leave_room_event(sid, data):
    """Let user leave a room"""
    room_name = data.get('room')
    
    if not room_name:
        return
    
    session = await sio.get_session(sid)
    username = session.get('username', 'Unknown')
    
    # Leave the room
    await sio.leave_room(sid, room_name)
    
    # Track membership
    if room_name in room_members:
        room_members[room_name].discard(sid)
    
    print(f"🚪 {username} left room '{room_name}'")
    
    # Notify room members
    await sio.emit('user_left_room', {
        'username': username,
        'room': room_name,
        'message': f'{username} left {room_name}'
    }, room=room_name)
    
    # Confirm to user
    await sio.emit('room_left', {
        'room': room_name,
        'message': f'You left {room_name}'
    }, to=sid)

@sio.event
async def get_room_users(sid, data):
    """Get list of users in a room"""
    room_name = data.get('room', 'general')
    
    usernames_in_room = []
    for user_sid in room_members.get(room_name, set()):
        user_session = await sio.get_session(user_sid)
        usernames_in_room.append(user_session.get('username', 'Unknown'))
    
    await sio.emit('room_user_list', {
        'room': room_name,
        'users': usernames_in_room,
        'count': len(usernames_in_room)
    }, to=sid)

@sio.event
async def disconnect(sid):
    """Handle disconnection - cleanup rooms"""
    # Get username before cleanup
    try:
        session = await sio.get_session(sid)
        username = session.get('username', 'Unknown')
    except:
        username = 'Unknown'
    
    # Remove from all room tracking
    rooms_to_notify = []
    for room_name, members in room_members.items():
        if sid in members:
            members.discard(sid)
            rooms_to_notify.append(room_name)
    
    print(f"❌ {username} disconnected")
    
    # Notify all rooms user was in
    for room_name in rooms_to_notify:
        await sio.emit('user_left', {
            'username': username,
            'room': room_name,
            'message': f'{username} left the chat'
        }, room=room_name)
        
        # Update user list for this room
        usernames_in_room = []
        for user_sid in room_members.get(room_name, set()):
            try:
                user_session = await sio.get_session(user_sid)
                usernames_in_room.append(user_session.get('username', 'Unknown'))
            except:
                pass
        
        await sio.emit('user_list', {
            'users': usernames_in_room,
            'count': len(usernames_in_room),
            'room': room_name
        }, room=room_name)

app.router.add_get('/', index)

if __name__ == '__main__':
    print("🚀 Starting chat server on http://localhost:5000")
    print("📝 Users will auto-join 'general' room on connect")
    web.run_app(app, port=5000)