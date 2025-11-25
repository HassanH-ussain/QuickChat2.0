import asyncio
import socketio
import aioconsole
async def main():
    sio = socketio.AsyncClient()
    
    @sio.event
    async def connect():
        print("✅ Connected to server!")
    
    @sio.event
    async def disconnect():
        print("❌ Disconnected from server")
    
    @sio.event
    async def user_joined(data):
        print(f"👋 {data['message']}")
    
    @sio.event
    async def user_left(data):
        print(f"👋 {data['message']}")

    @sio.event
    async def user_list(data):
        print(f"👥 Online ({data['count']}): {', '.join(data['users'])}")
    
    #Users' messages
    # @sio.event
    # async def new_message(data):
    #     print(f"{data['username']}: {data['text']}")
    
    username = input("Enter your username: ")
    print(f"Connecting as {username}...\n")
    
    await sio.connect('http://localhost:5000', auth={'username': username})

    print("Please type your messages or type 'quit'")
    # Send test messages
    try:
        while True:
            message = await aioconsole.ainput("> ")
            
            if message.lower() == 'quit':
                print("Disconnecting...")
                break
            
            if message.strip():
                await sio.emit('send_message', {
                    'text': message,
                    'room': 'general'
                })
    
    except KeyboardInterrupt:
        print("\nExiting...")
    
    await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())