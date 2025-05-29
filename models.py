from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class UserData:
    user_id: int
    username: str
    status: int = 0  # 0=Idle, 1=AFK, 2=Playing, 3=Editing, 4=Modding, 5=Multiplayer, 6=Watching, 7=Unknown, 8=Testing, 9=Submitting, 10=Paused, 11=Lobby, 12=Multiplaying, 13=OsuDirect
    status_text: str = ""
    beatmap_md5: str = ""
    mods: int = 0
    mode: int = 0  # 0=osu!, 1=Taiko, 2=CtB, 3=osu!mania
    beatmap_id: int = 0
    
    def __str__(self):
        return f"User({self.username}, ID: {self.user_id}, Status: {self.status})"

@dataclass
class UserInfo:
    id: int
    username: str
    created_at: str
    
@dataclass
class Message:
    sender: str
    sender_id: int
    target: str
    content: str
    timestamp: Optional[datetime] = None
    
@dataclass
class Channel:
    name: str
    description: str
    user_count: int = 0
    auto_join: bool = False