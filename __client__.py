import sys
import signal
import asyncio

from aioconsole import ainput

async def send_message(
    writer: asyncio.StreamWriter,
    room_id: str,
    username: str,
) -> bool:
    try:
        while True:
            message: str = await ainput(f"\t[Chatting] [#{room_id}] {username}: ")
            if len(message) > 512:
                print("\n\t🚫 Please try again, Messages must be no more than 512 characters long.\n")
                continue
                
            if "/" in message:
                match message:
                    case "/help":
                        print("\n\tList all commands for help command (in chat mode)")
                        print("\t✨ `/help` for list all commands that can using in chat cli (in chat mode).")
                        print("\t✨ `/exit` for exit from currently chat room.\n")
                        continue
                    
                    case "/exit":
                        writer.write(b"[#exit_room]")
                        await writer.drain()
                        
                        print(f"\n\t✅ Exit from `{room_id}` successfully\n")
                        return True
                    
                    case _:
                        print("\t❓ Please try again beacuse no such found the command to execution. (hint: /help)")
                        continue
            
            else:
                writer.write(message.encode())
                await writer.drain()
                
    except asyncio.CancelledError:
        pass
        
async def receive_message(
    reader: asyncio.StreamReader,
    room_id: str,
    username: str,
) -> None:
    try:
        while True:
            stream_data = await reader.read(1024)
            if not stream_data:
                break
            
            if username.encode() in stream_data:
                continue
            else: 
                sys.stdout.write('\r' + ' ' * 80 + '\r')

                print(f"\t{stream_data.decode().strip()}")

                sys.stdout.write(f"\t[Chatting] [#{room_id}] {username}: ")
                sys.stdout.flush()
                
    except asyncio.CancelledError:
        pass
    
    return

async def username_prompt(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> str:
    stream_data = await reader.read(24)
    if b"[#ask_username_prompt]" in stream_data:
        while True:
            username: str = ""
            while len(username) < 5 or len(username) > 16:
                username = await ainput("\tLet's we know about your username ❓\n\t→ ")
                if len(username) < 5:
                    print("\n\t🚫 Please try again, Username must be no less than 5 characters long.")
                    
                elif len(username) > 16:
                    print("\n\t🚫 Please try again, Username must be no more than 16 characters long.")
                
            writer.write(username.encode())
            await writer.drain()
            
            print(f"\n\t🌱 Verifying the username ({username})...")
            await asyncio.sleep(1)
            
            stream_data = await reader.read(42)
            if b"[#duplicated_username]" in stream_data:
                print("\n\t🚫 Please try again, The username was taken.\n")
                continue
            
            if b"[#verified_username]" in stream_data:
                break
            
    return username

async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        print("\n\t🎉 Chat CLI [v1.0.0]")
        print("\tBefore you use our Chat CLI, you need to set up a name for yourself.\n")
        username = await username_prompt(reader=reader, writer=writer)
        
        print("\n\t🌱 Retriving initial data and all chat rooms...\n\n\t", end="")
        await asyncio.sleep(1)
        
        stream_data = await reader.read(4096)
        print(stream_data.decode().replace("t]", ""))
        
        while True:
            try:
                command_executor: str = await ainput(f"\t[Idle] {username} ~ → ")
            except EOFError:
                print("\t❌ Input stream closed. Exiting...")
                break
                
            match command_executor.strip():
                case "/help":
                    print("\n\tList all commands for help command (in idle mode)")
                    print("\t✨ `/help` for list all commands that can using in chat cli (in idle mode).")
                    print("\t✨ `/list` for list all rooms available in chat server.")
                    print("\t✨ `/connect` for connect a chat room by room id.")
                    print("\t✨ `/create` for create a room.")
                    print("\t✨ `/remove` for remove a room.")
                    print("\t✨ `/exit` for exit from chat cli.\n")
                    
                case "/list":
                    writer.write(command_executor.encode())
                    await writer.drain()
                    
                    stream_data = await reader.read(8196)
                    print(stream_data.decode())
                    
                case "/connect":
                    writer.write(command_executor.encode())
                    await writer.drain()
                    
                    print("\n\t🧭 Select a room for create a conversation by entering the room id")
                    
                    room_id: str = ""
                    try:
                        room_id = await ainput(f"\t(Using the room id) → ")
                    except EOFError:
                        print("\t❌ Input stream closed. Exiting...")
                        break
                    
                    writer.write(room_id.encode())
                    await writer.drain()
                    
                    print(f"\n\t🌱 Checking availability...")
                    await asyncio.sleep(1)
                    
                    stream_data = await reader.read(64)
                    if b"[#no_available_room]" in stream_data:
                        print("\n\t🚫 The room doesn't exists, Please try again.\n")
                        continue
                    
                    print(f"\t🌱 Checking the room status...\n")
                    await asyncio.sleep(1)
                    
                    stream_data = await reader.read(64)
                    if b"[#room_removing]" in stream_data:
                        print("\t🚫 The room doesn't open because the room is removing, Please try again.\n")
                        continue
                    
                    writer.write(username.encode())
                    await writer.drain()
                    
                    print("\t📣 In chatting, You can use commands. If you don't know the command, use `/help` for help.")
                    print("\tIf you want to exit from this room, Use `/exit` to exit this chat room.\n")
                    print(f"\t🥂 {username} has joined the chat room.\n")
                    
                    send_task = asyncio.create_task(
                        send_message(
                            writer=writer,
                            username=username,
                            room_id=room_id,
                        )
                    )
                    receive_task = asyncio.create_task(
                        receive_message(
                            reader=reader,
                            username=username,
                            room_id=room_id,
                        )
                    )
                    
                    done, pending = await asyncio.wait(
                        [send_task, receive_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()
                    
                    await asyncio.gather(*pending, return_exceptions=True)
                    
                    if send_task in done and await send_task:
                        pass
                    
                case "/create":
                    writer.write(command_executor.encode())
                    await writer.drain()
                    
                    print("\n\t🔮 Before create a room, You must set a room title to describe about your room")
                    room_title: str = ""
                    try:
                        room_title = await ainput(f"\t(Your room title) → ")
                    except EOFError:
                        print("\t❌ Input stream closed. Exiting...")
                        break
                    
                    writer.write(room_title.encode())
                    await writer.drain()
                    
                    print(f"\n\t🌱 Creating `{room_title}` room, Please wait for a moment...")
                    await asyncio.sleep(2)
                    
                    stream_data = await reader.read(128)
                    if b"[#create_room_successfully]" in stream_data:
                        print(f"\n\t✅ Create `{room_title}` room was successfully!\n")
                        
                case "/remove":
                    writer.write(command_executor.encode())
                    await writer.drain()
                    
                    print("\n\t🔮 Before remove a room, You must specific a room id that do you want to remove")
                    room_id: str = ""
                    try:
                        room_id = await ainput(f"\t(Using the room id) → ")
                    except EOFError:
                        print("\t❌ Input stream closed. Exiting...")
                        break
                    
                    writer.write(room_id.encode())
                    await writer.drain()
                    
                    print(f"\n\t🌱 Chat room deletion is in progress (#{room_id}), Please wait a moment...")
                    await asyncio.sleep(1)
                    
                    stream_data = await reader.read(1024)
                    if b"[#no_available_room]" in stream_data:
                        print("\n\t🚫 The room doesn't exists, Please try again.")
                        continue
                    
                    await asyncio.sleep(1)
                    
                    print(f"\t✅ The room removed for #{room_id} was successfully!\n")
                    
                case "/exit":
                    writer.write(b"[#exit_cli]")
                    await writer.drain()
                    
                    print("\n\t📅 Exiting from chat CLI...\n")
                    break
                
                case "":
                    pass
                
                case _:
                    print("\t❓ Please try again beacuse no such found the command to execution. (hint: /help)")

    finally:
        print("\n\t🔒 Disconnecting from the server...")
        
        writer.close()
        await writer.wait_closed()
        
        print("\n\t✅ Disconnected successfully!")

async def main():
    try:
        reader, writer = await asyncio.open_connection('localhost', 9000)
        await handle_connection(reader, writer)
        
    except ConnectionRefusedError:
        print("\n\tUnable to connect to the server. Is it running?")
        
    except asyncio.CancelledError:
        print("\n\tClient operation cancelled.")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    main_task = loop.create_task(main())
    
    def signal_handler():
        main_task.cancel()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        loop.run_until_complete(main_task)
        
    except asyncio.CancelledError:
        pass
    
    finally:
        loop.close()