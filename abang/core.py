import json
from cachetools import cached, TTLCache

from wx_sdk import WechatBot
from wx_sdk import MSGType


class GameData(dict):
    pass


class ChannelContext(object):

    wechat_bot = WechatBot()

    def __init__(self, channel_id, apps=None):
        self.channel_id = channel_id
        self.apps = apps or []
        self.winner = GameData()

    @cached(cache=TTLCache(maxsize=500, ttl=86400))
    def get_member_nick(self, wx_id):
        resp = self.wechat_bot.get_member_nick(wx_id, self.channel_id)
        content = resp['content']
        content_json = json.loads(content)
        return content_json['nick']

    def get_channel_member_ids(self):
        resp = self.wechat_bot.get_memberid()
        content = resp['content']
        for info in content:
            if info['room_id'] == self.channel_id:
                return info['member']
        return []

    def reply(self, reply_content):
        self.wechat_bot.send_txt_msg(to=self.channel_id, content=reply_content)

    def reply_at(self, reply_content, wx_id):
        nickname = self.get_member_nick(wx_id)
        self.wechat_bot.send_at_msg(
            wx_id=wx_id,
            room_id=self.channel_id,
            content=reply_content,
            nickname=nickname)

    def collect_winner(self, app_name, wx_id, count=1):
        if app_name not in self.winner:
            self.winner[app_name] = {}
        self.winner[app_name][wx_id] += count


class PCMessage(object):
    def __init__(self, body):
        self.body = body

    @property
    def content(self):
        return self.body['content']

    @property
    def channel_id(self):
        return self.body.get('id2')

    @property
    def sender_id(self):
        return self.body['id1']

    @property
    def is_group(self):
        return self.channel_id.endswith('@chatroom')

    @property
    def msg_type(self):
        return self.body['type']

    @property
    def is_heartbeat(self):
        return self.msg_type == MSGType.HEART_BEAT


class WechatyMessage(object):

    def __init__(self, msg):
        self.msg = msg

    @property
    def content(self):
        return self.body['content']

    @property
    def channel_id(self):
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
