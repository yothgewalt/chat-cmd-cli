import signal

import string
import random
import asyncio

from datetime import datetime

class Participant(object):
    def __init__(
        self,
        username: str,
        address: tuple,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        self.username = username
        self.address = address
        
        self.reader = reader
        self.writer = writer
        
class RoomStatus(object):
    def __init__(self, name: str) -> None:
        self.name = name
        
    def __str__(self) -> str:
        return self.name
    
ROOM_OPENED_STATUS = RoomStatus("opened")
ROOM_REMOVING_STATUS = RoomStatus("removing")

class RoomMetadata(object):
    def __init__(self, id: str, title: str) -> None:
        self.id = id
        self.title = title
        self.status = ROOM_OPENED_STATUS
        
        self.participants: list[Participant] = []
        
        
    def get_total_of_participants(self) -> int:
        return len(self.participants)
    
    
    def get_all_participants(self) -> list[Participant]:
        return self.participants
    
    
    def get_all_username_participants(self) -> list[str]:
        usernames: list[str] = []
        for pc in self.participants:
            usernames.append(pc.username)
        
        return usernames
    
    
    def exists_username_participant(self, username: str) -> bool:
        usernames: list[str] = self.get_all_username_participants()
        return username in usernames
    
        
    def add_participant(self, pariticpant: Participant) -> None:
        return self.participants.append(pariticpant)
    
        
    def remove_participant(self, username: str) -> None:
        for pc in self.participants:
            if pc.username == username:
                self.participants.remove(pc)
                return
          
class Room:
    __length_of_room_id__: int = 6
    __rooms__: dict[str, RoomMetadata] = {}
    
    
    def __room_id_generator(self, n: int) -> str:
        return "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n))
    

    def exists_room(self, id) -> bool:
        return id in self.__rooms__
    
    
    def get_room(self, id) -> dict[str, RoomMetadata] | None:
        if id in self.__rooms__:
            return self.__rooms__[id]
        
        return None
    
    
    def get_total_of_rooms(self) -> int:
        return len(self.__rooms__)
    
    
    def get_all_room(self) -> dict[str, RoomMetadata]:
        return self.__rooms__
    
    
    def add_participant_to_room(self, room_id: str, participant: Participant) -> None:
        self.__rooms__[room_id].add_participant(pariticpant=participant)
    
    
    def remove_participant_from_room(self, room_id: str, username: str) -> None:
        self.__rooms__[room_id].remove_participant(username=username)
    
    
    def get_all_username_participants(self, room_id: str) -> list[str]:
        for id, metadata in self.__rooms__.items():
            if id == room_id:
                usernames = metadata.get_all_username_participants()
                return usernames
            
    
    def get_total_of_participants(self, room_id: str) -> int:
        for id, metadata in self.__rooms__.items():
            if id == room_id:
                total_of_participants = metadata.get_total_of_participants()
                return total_of_participants
    
    
    def create_room(self, title: str) -> None:
        room_id = self.__room_id_generator(self.__length_of_room_id__)
        self.__rooms__[room_id] = RoomMetadata(id=room_id, title=title)
        return
    
    
    def set_status_room(self, room_id: str, status: RoomStatus) -> None:
        self.__rooms__[room_id].status = status
        return
    
    
    def remove_room(self, room_id: str) -> None:        
        del self.__rooms__[room_id]
        return
    
    
    def get_room_status(self, room_id: str) -> RoomStatus:
        return self.__rooms__[room_id].status

class Chat(Room):
    __usernames__: list[str] = []
    
    async def __ask_username_prompt(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> str:
        while True:
            username_prompt_message: str = "[#ask_username_prompt]"
            writer.write(username_prompt_message.encode())
            await writer.drain()
                
            stream_data = await reader.read(1024)
            username_participant = stream_data.decode().strip()
            
            if username_participant in self.__usernames__:
                duplicated_username: str = "[#duplicated_username]"
                
                writer.write(duplicated_username.encode())
                await writer.drain()
                continue
            
            verified_username: str = "[#verified_username]"
            writer.write(verified_username.encode())
            await writer.drain()
            
            break
        
        self.__usernames__.append(username_participant)
        
        verified_username: str = "[#ask_username_prompt]"
        writer.write(verified_username.encode())
        
        return username_participant
    
    
    async def __list_all_rooms_available(self, writer: asyncio.StreamWriter) -> None:
        total_rooms = self.get_total_of_rooms()
        available_message = f"\n\tAll rooms available ({total_rooms} rooms)\n"
        if total_rooms < 1:
            available_message += "\t🚫 There are no rooms available.\n"
        else:
            rooms = self.get_all_room()
            for id, metadata in rooms.items():
                available_message += f"\t→ [ID: {id}] {metadata.title} ({metadata.get_total_of_participants()} participants)\n"
            
        encoded_message = available_message.encode()
        if len(encoded_message) > 8196:
            writer.write(b"\n\tUnable to show all rooms available because encode message is too large!\n")
            await writer.drain()
            
        writer.write(encoded_message)
        await writer.drain()
        

    async def boardcast_message_to_room(self, room_id: str, message: bytes) -> None:
        rooms = self.get_all_room()
        if room_id in rooms:
            metadata = rooms[room_id]
            participants = metadata.get_all_participants()

            if participants:
                for pc in participants:
                    try:
                        pc.writer.write(message)
                        await pc.writer.drain()
                        
                    except Exception as e:
                        print(f"Failed to send message to {pc.username}: {e}")
        
        return
        
        
    async def participant_callback(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        address: tuple = writer.get_extra_info("peername")
        username_participant: str = await self.__ask_username_prompt(reader=reader, writer=writer)
                
        welcome_message = f"Hello {username_participant}, Welcome to the chat server that keep simple to use!\n"
        welcome_message += "\tIf you want to know about the commands, use `/help` to show all commands.\n"
        
        writer.write(welcome_message.encode())
        await writer.drain()
        
        await self.__list_all_rooms_available(writer=writer)
        
        while True:
            current_timestamp = datetime.now()
            formatted_timestamp = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            stream_data = await reader.read(1024)
            command_execution = stream_data.decode().strip()
            
            match command_execution:
                case "/list":
                    await self.__list_all_rooms_available(writer=writer)
                    continue
                    
                case "/connect":
                    stream_data = await reader.read(1024)
                    room_id = stream_data.decode().strip().upper()
                    
                    is_exists = self.exists_room(room_id)
                    if not is_exists:
                        writer.write(b"[#no_available_room]")
                        await writer.drain()
                        continue
                    
                    else:
                        writer.write(b"[#continue]")
                        await writer.drain()
                        
                    await asyncio.sleep(2)
                          
                    got_status = self.get_room_status(room_id=room_id)
                    if got_status == ROOM_REMOVING_STATUS:
                        writer.write(b"[#room_removing]")
                        await writer.drain()
                        continue
                    
                    else:
                        writer.write(b"[#continue]")
                        await writer.drain()
                    
                    stream_data = await reader.read(64)
                    username_joined = stream_data.decode().strip()
                    
                    joined_message: str = f"\n\t🥂 {username_joined} has joined the chat room.\n"
                    asyncio.create_task(
                        self.boardcast_message_to_room(
                            room_id=room_id,
                            message=joined_message.encode()
                        )
                    )
                    
                    self.add_participant_to_room(
                        room_id=room_id,
                        participant=Participant(
                            username=username_participant,
                            address=address,
                            reader=reader,
                            writer=writer
                        )
                    )
                    
                    while True:
                        stream_data = await reader.read(1024)
                                                    
                        if b"[#exit_room]" in stream_data:
                            self.remove_participant_from_room(room_id=room_id, username=username_participant)
                            leave_message: str = f"\n\t💥 {username_participant} has left from the chat room.\n"
                            
                            await asyncio.sleep(0.5)
                            asyncio.create_task(
                                self.boardcast_message_to_room(
                                    room_id=room_id,
                                    message=leave_message.encode()
                                )
                            )
                            
                            room_status: RoomStatus = self.get_room_status(room_id=room_id)
                            total_of_participants: int = self.get_total_of_participants(room_id=room_id)
                            if total_of_participants < 1 and room_status is ROOM_REMOVING_STATUS:
                                self.remove_room(room_id=room_id)
                            
                            break
                        
                        message = f"[{formatted_timestamp}] {username_participant}: {stream_data.decode().strip()}"
                        asyncio.create_task(
                            self.boardcast_message_to_room(
                                room_id=room_id,
                                message=message.encode()
                            )
                        )
                        
                    continue
                
                case "/create":
                    stream_data = await reader.read(1024)
                    room_title = stream_data.decode().strip()
                    
                    self.create_room(title=room_title)
                    
                    writer.write(b"[#create_room_successfully]")
                    await writer.drain()
                    
                    continue
                    
                case "/remove":
                    stream_data = await reader.read(1024)
                    room_id = stream_data.decode().strip().upper()
                    
                    is_exists = self.exists_room(room_id)
                    if not is_exists:
                        writer.write(b"[#no_available_room]")
                        await writer.drain()
                        continue
                    else:
                        writer.write(b"[#continue]")
                        await writer.drain()
                        
                    self.set_status_room(room_id=room_id, status=ROOM_REMOVING_STATUS)
                    
                    participants: list[str] = self.get_all_username_participants(room_id=room_id)
                    if len(participants) < 1:
                        self.remove_room(room_id=room_id)
                        
                    continue
                
                case "/exit":
                    stream_data = await reader.read(1024)
                    if b"[#exit_cli]" in stream_data:
                        print(f"\n💡 {username_participant} has requested to exit.\n")
                        break
            
            continue
        
        print(f"❗️ \n{username_participant} has disconnected.\n")
        writer.close()
        await writer.wait_closed()
        
class Server(Chat):
    def __init__(self, hostname: str, port: int) -> None:
        super().__init__()
        
        self.hostname = hostname
        self.port = port
        self.server = None
        self.clients: set[asyncio.Task] = set()
        
    async def callback(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_task = asyncio.create_task(self.participant_callback(reader, writer))
        self.clients.add(client_task)
        
        try:
            await client_task
            
        except asyncio.CancelledError:
            pass
        
        finally:
            self.clients.remove(client_task)
            
            writer.close()
            await writer.wait_closed()
        
    async def run(self):
        self.server = await asyncio.start_server(
            client_connected_cb=self.participant_callback,
            host=self.hostname,
            port=self.port
        )
        print(f"\n🎉 Chat CLI is listening on {self.hostname}:{self.port}\n")
        
        async with self.server:
            await self.server.serve_forever()
            
    async def shutdown(self):
        print("\n⚡️ Chat CLI is shutting down...")
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        for client in self.clients:
            client.cancel()
        
        await asyncio.gather(*self.clients, return_exceptions=True)
        
        print("\n✅ Server has been shut down gracefully.")

async def main():
    TCP_HOSTNAME: str = "127.0.0.1"
    TCP_PORT: int = 9000
    
    server = Server(hostname=TCP_HOSTNAME, port=TCP_PORT)
    
    def signal_handler():
        asyncio.create_task(server.shutdown())
        
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    
    try:
        await server.run()
        
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(main=main())