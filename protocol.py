import struct
import io
from typing import List, Dict, Any
from models import Channel

class BanchoProtocol:
    
    @staticmethod
    def write_string(s: str) -> bytes:
        if not s:
            return bytes([0x00])
        
        encoded = s.encode('utf-8')
        length = len(encoded)
        result = bytearray([0x0b])
        
        while True:
            b = length & 0x7f
            length >>= 7
            if length == 0:
                result.append(b)
                break
            result.append(b | 0x80)
        
        result.extend(encoded)
        return bytes(result)
    
    @staticmethod
    def write_int_list(int_list: List[int]) -> bytes:
        result = bytearray()
        result.extend(struct.pack('<H', len(int_list)))
        for item in int_list:
            result.extend(struct.pack('<I', item))
        return bytes(result)
    
    @staticmethod
    def read_int_list_from_stream(stream: io.BytesIO) -> List[int]:
        length_bytes = stream.read(2)
        if len(length_bytes) < 2:
            return []
        
        length = struct.unpack('<H', length_bytes)[0]
        int_list = []
        
        for _ in range(length):
            int_bytes = stream.read(4)
            if len(int_bytes) < 4:
                break
            int_list.append(struct.unpack('<I', int_bytes)[0])
        
        return int_list
    
    @staticmethod
    def read_bancho_string(data: bytes) -> str:
        stream = io.BytesIO(data)
        return BanchoProtocol.read_bancho_string_from_stream(stream)
    
    @staticmethod
    def read_bancho_string_from_stream(stream: io.BytesIO) -> str:
        marker_bytes = stream.read(1)
        
        if not marker_bytes:
            return ""
            
        marker = marker_bytes[0]
        
        if marker == 0x00:
            return ""
        
        if marker != 0x0b:
            raise ValueError(f"Unexpected Bancho string marker: {marker}")
        
        length = 0
        shift = 0
        
        while True:
            b_bytes = stream.read(1)
            if not b_bytes:
                break
            b = b_bytes[0]
            length |= (b & 0x7F) << shift
            if (b & 0x80) == 0:
                break
            shift += 7
        
        string_bytes = stream.read(length)
        return string_bytes.decode('utf-8')
    
    @staticmethod
    def create_packet(packet_id: int, content: bytes) -> bytes:
        compression = 0
        return struct.pack('<HbI', packet_id, compression, len(content)) + content


class PacketBuilder:
    
    @staticmethod
    def protocol_negotiation(version: int) -> bytes:
        content = struct.pack('<I', version)
        return BanchoProtocol.create_packet(75, content)
    
    @staticmethod
    def login_reply(user_id: int) -> bytes:
        content = struct.pack('<i', user_id)
        return BanchoProtocol.create_packet(5, content)
    
    @staticmethod
    def login_permissions(permissions: int) -> bytes:
        content = struct.pack('<I', permissions)
        return BanchoProtocol.create_packet(71, content)
    
    @staticmethod
    def user_presence(user_id: int, username: str, timezone: int, 
                     country_id: int, permissions: int, mode: int, 
                     longitude: float, latitude: float, rank: int) -> bytes:
        bancho_permissions = permissions | (mode << 5)

        content = (
            struct.pack("<i", user_id) +
            BanchoProtocol.write_string(username) +
            struct.pack("<B", (timezone + 24) & 0xFF) + 
            struct.pack("<B", country_id) +
            struct.pack("<B", permissions | (mode << 5)) + 
            struct.pack("<f", longitude) +
            struct.pack("<f", latitude) +
            struct.pack("<i", rank)
        )
        return BanchoProtocol.create_packet(83, content)
    
    @staticmethod
    def user_presence_single(user_id: int) -> bytes:
        content = struct.pack('<i', user_id)
        return BanchoProtocol.create_packet(95, content)
    
    @staticmethod
    def user_presence_bundle(user_ids: List[int]) -> bytes:
        content = BanchoProtocol.write_int_list(user_ids)
        return BanchoProtocol.create_packet(96, content)
    
    @staticmethod
    def user_stats(user_id: int, status: int, status_text: str, 
                  beatmap_md5: str, mods: int, mode: int, beatmap_id: int,
                  ranked_score: int, accuracy: float, playcount: int,
                  total_score: int, rank: int, pp: int) -> bytes:

        if accuracy > 1.0:
            accuracy_normalized = accuracy / 100.0
        else:
            accuracy_normalized = accuracy
        
        accuracy_normalized = max(0.0, min(1.0, accuracy_normalized))
    
        content = (
            struct.pack("<i", user_id) +
            struct.pack("<B", status) +
            BanchoProtocol.write_string(status_text if status_text else "") +
            BanchoProtocol.write_string(beatmap_md5 if beatmap_md5 else "") +
            struct.pack("<I", mods) +
            struct.pack("<B", mode) +
            struct.pack("<i", beatmap_id) +
            struct.pack("<Q", max(0, ranked_score)) +
            struct.pack("<f", accuracy_normalized) +
            struct.pack("<i", max(0, playcount)) +
            struct.pack("<Q", max(0, total_score)) +
            struct.pack("<i", max(1, rank)) +
            struct.pack("<i", max(0, pp))
        )
        return BanchoProtocol.create_packet(11, content)
    
    @staticmethod
    def user_quit(user_id: int, quit_state: int = 0) -> bytes:
        content = struct.pack('<iB', user_id, quit_state)
        return BanchoProtocol.create_packet(12, content)
    
    @staticmethod
    def channel_join_success(channel_name: str) -> bytes:
        content = BanchoProtocol.write_string(channel_name)
        return BanchoProtocol.create_packet(64, content)
    
    @staticmethod
    def friends_list(friend_ids: List[int]) -> bytes:
        content = BanchoProtocol.write_int_list(friend_ids)
        return BanchoProtocol.create_packet(72, content)
    
    @staticmethod
    def channel_available(channel: Channel) -> bytes:
        content = (
            BanchoProtocol.write_string(channel.name) +
            BanchoProtocol.write_string(channel.description) +
            struct.pack('<H', channel.user_count)
        )
        packet_id = 67 if channel.auto_join else 65
        return BanchoProtocol.create_packet(packet_id, content)
    
    @staticmethod
    def channel_info_complete() -> bytes:
        return BanchoProtocol.create_packet(89, b'')
    
    @staticmethod
    def send_message(target: str, message: str, sender: str, sender_id: int) -> bytes:
        content = (
            BanchoProtocol.write_string(sender) +
            BanchoProtocol.write_string(message) +
            BanchoProtocol.write_string(target) +
            struct.pack('<I', sender_id)
        )
        return BanchoProtocol.create_packet(7, content)
    
    @staticmethod
    def ping() -> bytes:
        return BanchoProtocol.create_packet(8, b'')
    
    @staticmethod
    def notification(message: str) -> bytes:
        content = BanchoProtocol.write_string(message)
        return BanchoProtocol.create_packet(24, content)