from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    TYPE_CHECKING
)

from wechaty.user import Message, Room
from wechaty import Wechaty, Contact, FileBox, MiniProgram, UrlLink


class GameData(dict):
    pass


class ChannelContext(object):

    def __init__(self, channel_id: str, is_group: bool, apps=None):
        self.channel_id = channel_id
        self.is_group = is_group
        self.apps = apps or []
        self.winner = GameData()
        self.bot: Optional[Wechaty] = None

    def set_bot(self, bot: Wechaty):
        self.bot = bot

    async def get_channel(self) -> Union[Room, Contact]:
        if self.is_group:
            room: Room = self.bot.Room.load(self.channel_id)
            await room.ready()
            return room
        else:
            contact: Contact = self.bot.Contact.load(self.channel_id)
            await contact.ready()
            return contact

    async def get_member_nick(self, wx_id) -> str:
        member: Contact = self.bot.Contact.load(wx_id)
        await member.ready()
        if self.is_group:
            room: Room = self.bot.Room.load(self.channel_id)
            await room.ready()
            return await room.alias(member)
        return member.name

    async def get_channel_member_ids(self):
        if not self.is_group:
            return []
        room: Room = self.bot.Room.load(self.channel_id)
        await room.ready()
        return await room.member_list()

    async def say(self,
                  some_thing: Union[str, Contact, FileBox, MiniProgram, UrlLink],
                  mention_ids: Optional[List[str]] = None
                  ) -> Optional[Message]:
        if self.is_group:
            room: Room = self.bot.Room.load(self.channel_id)
            await room.ready()
            return await room.say(some_thing=some_thing, mention_ids=mention_ids)
        else:
            contact: Contact = self.bot.Contact.load(self.channel_id)
            await contact.ready()
            return await contact.say(some_thing)

    def collect_winner(self, app_name, wx_id, count=1):
        if app_name not in self.winner:
            self.winner[app_name] = defaultdict(int)
        self.winner[app_name][wx_id] += count


class WechatyMessage(object):

    def __init__(self, msg: Message):
        self.msg = msg

    @property
    def content(self):
        return self.msg.text()

    @property
    def channel_id(self) -> str:
        room = self.msg.room()
        if room is not None:
            channel_id = room.room_id
        else:
            talker = self.msg.talker()
            if talker is None:
                raise RuntimeError('Message must be from room/contact')
            channel_id = talker.contact_id
        return channel_id

    @property
    def sender_id(self):
        talker = self.msg.talker()
        return talker.contact_id

    @property
    def is_group(self):
        return self.msg.room() is not None

    @property
    def is_text_msg(self):
        return self.msg.type() == 1  # TODO use const

    @property
    def msg_type(self):
        return self.msg.type()

    @property
    def is_heartbeat(self):
        return False
