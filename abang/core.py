import json
from cachetools import cached, TTLCache

from wx_sdk import WechatBot
from wx_sdk import MSGType


class ChannelContext(object):

    wechat_bot = WechatBot()

    def __init__(self, channel_id, apps=None):
        self.channel_id = channel_id
        self.apps = apps or []

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


class Message(object):
    def __init__(self, body):
        self.body = body
        self.ctx = None

    def set_ctx(self, ctx):
        self.ctx = ctx

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
