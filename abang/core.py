import json
from cachetools import cached, TTLCache
from typing import Optional

from wechaty.user import Message, Room
from wechaty import Wechaty, Contact


class GameData(dict):
    pass


class ChannelContext(object):

    def __init__(self, channel_id, apps=None):
        self.channel_id = channel_id
        self.apps = apps or []
        self.winner = GameData()
        self._bot: Optional[Wechaty] = None

    def set_bot(self, bot: Wechaty):
        self._bot = bot

    @cached(cache=TTLCache(maxsize=500, ttl=86400))
    def get_member_nick(self, wx_id):
        raise NotImplementedError
        '''
        resp = self.wechat_bot.get_member_nick(wx_id, self.channel_id)
        content = resp['content']
        content_json = json.loads(content)
        return content_json['nick']
        '''

    def get_channel_member_ids(self):
        raise NotImplementedError
        '''
        resp = self.wechat_bot.get_memberid()
        content = resp['content']
        for info in content:
            if info['room_id'] == self.channel_id:
                return info['member']
        return []
        '''

    def reply(self, reply_content):
        raise NotImplementedError
        '''
        self.wechat_bot.send_txt_msg(to=self.channel_id, content=reply_content)
        '''

    def reply_at(self, reply_content, wx_id):
        # nickname = self.get_member_nick(wx_id)
        '''
        self.wechat_bot.send_at_msg(
            wx_id=wx_id,
            room_id=self.channel_id,
            content=reply_content,
            nickname=nickname)
        '''

    def collect_winner(self, app_name, wx_id, count=1):
        if app_name not in self.winner:
            self.winner[app_name] = {}
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
