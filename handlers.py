import io
import struct
from typing import Optional, Dict, List
from models import UserData, Message, Channel
from protocol import BanchoProtocol, PacketBuilder


class LoginHandler:
    
    def __init__(self, db_manager, token_manager):
        self.db_manager = db_manager
        self.token_manager = token_manager
    
    def handle_login(self, body: bytes) -> tuple[bool, bytes, Optional[str]]:
        try:
            if not body:
                print("empty login body")
                return False, PacketBuilder.login_reply(-1), None
                
            data = body.decode('utf-8')
            parts = data.strip().split('\n')
            
            if len(parts) < 3:
                print("invalid login format")
                return False, PacketBuilder.login_reply(-1), None
            
            username = parts[0].strip()
            password_md5 = parts[1].strip()
            client_info = parts[2].strip()
            
            print(f"login attempt: {username}")
            print(f"client Info: {client_info}")
            
            # check in db
            user_id = self.db_manager.validate_user(username, password_md5)
            
            if user_id:
                print(f"{username}: the user is connecteduhh successfullay ({user_id})")
                
                token = f"osutokenv1_{username}_{user_id}"
                user_data = UserData(user_id, username)
                self.token_manager.add_user(token, user_data)
                
                response_data = self._build_login_response(user_id, username)
                return True, response_data, token
            else:
                print(f"login fail for {username}: wrong pw")
                return False, PacketBuilder.login_reply(-1), None
                
        except Exception as e:
            print(f"login error: {e}")
            return False, PacketBuilder.login_reply(-1), None
    
    def _build_login_response(self, user_id: int, username: str) -> bytes:
        response_data = bytearray()
        
        response_data.extend(PacketBuilder.protocol_negotiation(19))
        
        response_data.extend(PacketBuilder.login_reply(user_id))
        
        response_data.extend(PacketBuilder.login_permissions(4))
        
        response_data.extend(PacketBuilder.user_presence(
            user_id, username, 5, 94, 4, 0, 0.0, 0.0, 2100))
            
        response_data.extend(PacketBuilder.user_stats(
            user_id, 0, "Idle", "", 0, 0, 0,
            ranked_score=5000000,
            accuracy=97.54,
            playcount=123,
            total_score=8000000,
            rank=2100,
            pp=2100))

        online_users = self.token_manager.get_active_users()
        other_user_ids = []
        
        for token, other_user in online_users.items():
            if other_user.user_id != user_id:
                other_user_ids.append(other_user.user_id)
                # send presence for each online user
                response_data.extend(PacketBuilder.user_presence(
                    other_user.user_id, other_user.username, 5, 94, 4, 0, 0.0, 0.0, 2100))
                # send stats for each online user
                response_data.extend(PacketBuilder.user_stats(
                    other_user.user_id, other_user.status, other_user.status_text, 
                    other_user.beatmap_md5, other_user.mods, other_user.mode, 
                    other_user.beatmap_id, ranked_score=5000000, accuracy=97.54,
                    playcount=123, total_score=8000000, rank=2100, pp=2100))

        # send user presence bundle with everything
        if other_user_ids:
            response_data.extend(PacketBuilder.user_presence_bundle(other_user_ids))

        # homies
        response_data.extend(PacketBuilder.friends_list([]))
        
        # channelz
        main_channel = Channel("#osu", "Main chat", len(online_users) + 1, False)
        auto_join_channel = Channel("#osu", "Main chat", len(online_users) + 1, True)
        
        response_data.extend(PacketBuilder.channel_join_success("#osu"))
        
        response_data.extend(PacketBuilder.channel_available(main_channel))
        response_data.extend(PacketBuilder.channel_available(auto_join_channel))
        response_data.extend(PacketBuilder.channel_info_complete())
        
        return bytes(response_data)


# In handlers.py
class PacketHandler:
    
    def _handle_ping(self, user: UserData, data: bytes) -> bytes:
        return PacketBuilder.pong()
    
    def __init__(self, token_manager):
        self.token_manager = token_manager
        self.packet_handlers = {
            0: self._handle_change_status,
            2: self._handle_status_update,
            3: self._handle_request_status_update,
            4: self._handle_pong,
            25: self._handle_send_message,
            63: self._handle_join_channel,
            79: self._handle_receive_updates,
            85: self._handle_stats_request,
           
        }
    
    def process_packets(self, user: UserData, body: bytes) -> bytes:
        response_packets = bytearray()
        
        if not body:
            return bytes(response_packets)
        
        stream = io.BytesIO(body)
        
        while stream.tell() < len(body):
            try:
                remaining = len(body) - stream.tell()
                if remaining < 7:  
                    break
                
                packet_id_bytes = stream.read(2)
                if len(packet_id_bytes) < 2:
                    break
                    
                packet_id = struct.unpack('<H', packet_id_bytes)[0]
                compression = struct.unpack('<B', stream.read(1))[0]
                length = struct.unpack('<I', stream.read(4))[0]
                
                if length > remaining - 7: 
                    print(f"invalid packet length: {length}, remaining: {remaining}")
                    break
                    
                data = stream.read(length)
                
                print(f"received packet: ID={packet_id}, Length={length}")
                
                if packet_id in self.packet_handlers:
                    response = self.packet_handlers[packet_id](user, data)
                    if response:
                        response_packets.extend(response)
                else:
                    print(f"unhandled packet ID: {packet_id}")
                    
            except struct.error as e:
                print(f"error parsing packet: {e}")
                break
            except Exception as e:
                print(f"error processing packet: {e}")
                break
        
        return bytes(response_packets)
    
    def _broadcast_to_all_users(self, packet_data: bytes, exclude_user: Optional[UserData] = None) -> bytes:
        response_packets = bytearray()
        
        for token, user_data in self.token_manager.get_active_users().items():
            if exclude_user and user_data.user_id == exclude_user.user_id:
                continue
            response_packets.extend(packet_data)
        
        return bytes(response_packets)
    
    def _broadcast_to_channel(self, channel_name: str, message_packet: bytes, exclude_user: Optional[UserData] = None) -> bytes:
        response_packets = bytearray()
        
        for token, user_data in self.token_manager.get_active_users().items():
            if exclude_user and user_data.user_id == exclude_user.user_id:
                continue 
            response_packets.extend(message_packet)
        
        return bytes(response_packets)
    
    def _handle_change_status(self, user: UserData, data: bytes) -> Optional[bytes]:
        try:
            stream = io.BytesIO(data)
            status = struct.unpack('<B', stream.read(1))[0]
            status_text = BanchoProtocol.read_bancho_string_from_stream(stream)
            beatmap_md5 = BanchoProtocol.read_bancho_string_from_stream(stream)
            mods = struct.unpack('<I', stream.read(4))[0]
            mode = struct.unpack('<B', stream.read(1))[0]
            beatmap_id = struct.unpack('<i', stream.read(4))[0]
            
            print(f"update from: {user.username}: {status} - {status_text}")
            
            user.status = status
            user.status_text = status_text
            user.beatmap_md5 = beatmap_md5
            user.mods = mods
            user.mode = mode
            user.beatmap_id = beatmap_id
            
            stats_packet = PacketBuilder.user_stats(
                user.user_id, status, status_text, beatmap_md5, mods, mode, beatmap_id,
                ranked_score=5000000, accuracy=97.54, playcount=123,
                total_score=8000000, rank=2100, pp=2100)
            
            return self._broadcast_to_all_users(stats_packet, exclude_user=user)
            
        except Exception as e:
            print(f"error handling status change :  {e}")
        
        return None
    
    def _handle_request_status_update(self, user: UserData, data: bytes) -> Optional[bytes]:
        try:
            stream = io.BytesIO(data)
            user_ids = BanchoProtocol.read_int_list_from_stream(stream)
            
            print(f"status update request from {user.username} for users(s): {user_ids}")
            
            response_packets = bytearray()
            
            for requested_user_id in user_ids:
                for token, active_user in self.token_manager.get_active_users().items():
                    if active_user.user_id == requested_user_id:
                        stats_packet = PacketBuilder.user_stats(
                            active_user.user_id, active_user.status, active_user.status_text,
                            active_user.beatmap_md5, active_user.mods, active_user.mode,
                            active_user.beatmap_id, ranked_score=5000000, accuracy=97.54,
                            playcount=123, total_score=8000000, rank=2100, pp=2100)
                        response_packets.extend(stats_packet)
                        break
            
            return bytes(response_packets)
            
        except Exception as e:
            print(f"request handle error: {e}")
        
        return None
    
    def _handle_stats_request(self, user: UserData, data: bytes) -> Optional[bytes]:
        try:
            stream = io.BytesIO(data)
            user_ids = BanchoProtocol.read_int_list_from_stream(stream)
            
            print(f"stat request from {user.username} for user(s): {user_ids}")
            
            response_packets = bytearray()
            
            for requested_user_id in user_ids:
                user_found = False
                for token, active_user in self.token_manager.get_active_users().items():
                    if active_user.user_id == requested_user_id:
                        stats_packet = PacketBuilder.user_stats(
                            active_user.user_id, active_user.status, active_user.status_text,
                            active_user.beatmap_md5, active_user.mods, active_user.mode,
                            active_user.beatmap_id, ranked_score=5000000, accuracy=97.54,
                            playcount=123, total_score=8000000, rank=2100, pp=2100)
                        response_packets.extend(stats_packet)
                        user_found = True
                        break
                
            
            return bytes(response_packets)
            
        except Exception as e:
            print(f"stat request error: {e}")
        
        return None
    
    def _handle_receive_updates(self, user: UserData, data: bytes) -> Optional[bytes]:
        print(f"receive updates request from {user.username}")
        
        response_packets = bytearray()
        online_user_ids = []
        
        for token, online_user in self.token_manager.get_active_users().items():
            if online_user.user_id != user.user_id:
                online_user_ids.append(online_user.user_id)
                
                # send presence
                response_packets.extend(PacketBuilder.user_presence(
                    online_user.user_id, online_user.username, 5, 94, 4, 0, 0.0, 0.0, 2100))
                
                # send stats
                response_packets.extend(PacketBuilder.user_stats(
                    online_user.user_id, online_user.status, online_user.status_text,
                    online_user.beatmap_md5, online_user.mods, online_user.mode,
                    online_user.beatmap_id, ranked_score=5000000, accuracy=97.54,
                    playcount=123, total_score=8000000, rank=2100, pp=2100))
        
        # send user presence bundle
        if online_user_ids:
            response_packets.extend(PacketBuilder.user_presence_bundle(online_user_ids))
        
        return bytes(response_packets)
    
    def _handle_join_channel(self, user: UserData, data: bytes) -> Optional[bytes]:
        try:
            channel_name = BanchoProtocol.read_bancho_string(data)
            print(f"{user.username} wants to join channel: {channel_name}")
            
            if channel_name == "#osu":
                return PacketBuilder.channel_join_success(channel_name)
        except Exception as e:
            print(f"channel join error: {e}")
        
        return None

    def _handle_send_message(self, user: UserData, data: bytes) -> Optional[bytes]:
        try:
            stream = io.BytesIO(data)
            target = BanchoProtocol.read_bancho_string_from_stream(stream)
            message = BanchoProtocol.read_bancho_string_from_stream(stream)
            sending_client = BanchoProtocol.read_bancho_string_from_stream(stream)
        
            print(f"[Send Message] {user.username} -> {target}: {message}")
        
            if target.startswith("#"):
                message_packet = PacketBuilder.send_message(target, message, user.username, user.user_id)
                return self._broadcast_to_channel(target, message_packet, exclude_user=user)
                
        except Exception as e:
            print(f"Error handling send message: {e}")
    
        return None
    
    def _handle_status_update(self, user: UserData, data: bytes) -> Optional[bytes]:
        print(f"Deprecated status update from {user.username}")
        return None
    
    def _handle_pong(self, user: UserData, data: bytes) -> Optional[bytes]:
        print(f"pong from {user.username}")
        return None


class TokenManager:
    
    def __init__(self):
        self.active_tokens: Dict[str, UserData] = {}
    
    def add_user(self, token: str, user_data: UserData):
        self.active_tokens[token] = user_data
        print(f"new user session: {user_data.username} (total: {len(self.active_tokens)})")

    
    def get_user(self, token: str) -> Optional[UserData]:
        return self.active_tokens.get(token)
    
    def remove_user(self, token: str):
        if token in self.active_tokens:
            user = self.active_tokens[token]
            del self.active_tokens[token]
            print(f"removed user session: {user.username} (total: {len(self.active_tokens)})")
            
    
    def get_active_users(self) -> Dict[str, UserData]:
        return self.active_tokens.copy()