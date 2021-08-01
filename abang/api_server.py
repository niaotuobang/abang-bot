# FUCK windows
import _locale
_locale._getdefaultlocale = (lambda *args: ['zh_CN', 'utf8']) # noqa

import json
import time
from collections import defaultdict
from functools import cached_property
from random import choice

from cachetools import cached, TTLCache
from flask import Flask
from flask import request

from emoji_chengyu.chengyu import gen_one_emoji_pair
from emoji_chengyu.data import DataSource as ChengyuDataSource

from wx_sdk import WechatBot
from wx_sdk import MSGType


app = Flask(__name__)


class TinyApp(object):
    active = False

    MESSAGE_TYPES = (MSGType.RECV_TXT_MSG, )

    APP_NAME = None
    APP_DESC = None
    START_WORDS = ()
    STOP_WORDS = ()

    wechat_bot = WechatBot()

    def __init__(self):
        self.ctx = None

    def set_ctx(self, ctx):
        self.ctx = ctx

    @cached_property
    def play_desc(self):
        if not self.APP_NAME:
            return None

        desc = f'''{self.APP_NAME} \n触发词: {'、'.join(self.START_WORDS)}'''
        if self.STOP_WORDS:
            desc += f'''\n结束词: {'、'.join(self.STOP_WORDS)}'''
        if self.APP_DESC:
            desc += f'\n{self.APP_DESC}'
        return desc

    def need_handle(self, message):
        if message.msg_type in self.MESSAGE_TYPES:
            return True
        return False

    def check_active(self, message):
        if message.content in self.START_WORDS:
            self.set_active(True, message)
        elif message.content in self.STOP_WORDS:
            self.set_active(False, message)

    def set_active(self, active, message):
        if self.active == active:
            return

        print(self.__class__.__name__, ' self.active, active ', self.active, active)
        self.active = active
        if self.active:
            self.on_app_start(message)
        else:
            self.on_app_stop(message)

    def on_app_start(self, message):
        pass

    def on_app_stop(self, message):
        pass

    def check_next(self, message):
        if self.active:
            self.on_next(message)

    def on_next(self, message):
        pass


class Hello(TinyApp):
    APP_NAME = '打招呼'
    START_WORDS = ('阿邦', '毛毛', '阿邦你好', '邦邦')

    def on_next(self, message):
        reply_content = '让我来邦你'
        if message.is_group:
            nickname = self.ctx.get_member_nick(message.sender_id)
            self.wechat_bot.send_at_msg(
                wx_id=message.sender_id,
                room_id=message.channel_id,
                content=reply_content,
                nickname=nickname)
        else:
            self.wechat_bot.send_txt_msg(
                to=message.channel_id,
                content=reply_content)

        self.set_active(False, message)


class Repeat(TinyApp):

    APP_NAME = '复读机'
    START_WORDS = ('开始复读', '阿邦复读', '阿邦开始复读')
    STOP_WORDS = ('结束复读', '别复读了')

    def on_next(self, message):
        self.wechat_bot.send_txt_msg(
            to=message.channel_id,
            content=message.content)


class EmojiChengyu(TinyApp):
    APP_NAME = '表情猜成语'
    START_WORDS = ('开始表情猜成语', '阿邦表情猜成语', '阿邦表情成语', '开始抽象成语')
    STOP_WORDS = ('结束游戏', '结束表情猜成语')

    def on_app_start(self, message):
        self.game = {}
        self.game['winner'] = defaultdict(int)
        self.game['items'] = []
        self.game['checked'] = []
        self.game['last'] = None
        self.game['index'] = 0
        self.make_more_item()

        first_content = '最多{}个题目,每次问题20秒后提示1个字(也可发送"提示"触发), 45秒后公布答案(也可发送"我要答案"触发)'.format(
            len(self.game['items']))
        self.wechat_bot.send_txt_msg(
            to=message.channel_id,
            content=first_content)

        self.send_one_case(message)

    def on_app_stop(self, message):
        # TODO: send the winner
        self.game = {}

    def make_more_item(self):
        N = 60
        pairs = [gen_one_emoji_pair(search_count=500) for i in range(N)]
        pairs = filter(None, pairs)
        pairs = filter(lambda pair: len(pair['words']) == 4, pairs)
        pairs = list(pairs)
        pairs.sort(key=lambda pair: pair['emojis'].count(None))

        pairs2 = []
        used_words = {}
        for pair in pairs:
            if pair['word'] not in used_words:
                pairs2.append(pair)
                used_words[pair['word']] = True

        self.game['items'] = pairs2[:20]

    def send_one_case(self, message):
        if len(self.game['items']) == 0:
            return False

        item = self.game['items'].pop(0)
        self.game['index'] += 1

        question = '第{} 题 ({}个字): {}'.format(
            self.game['index'],
            len(item['word']),
            item['emoji'])

        # TODO: 考虑 message 自带 reply 方法
        self.wechat_bot.send_txt_msg(to=message.channel_id, content=question)
        self.game['last'] = {
            'item': item,
            'create_time': time.time(),
            'tip': False,
        }

        print(item['word'], item['emoji'])
        return True

    def check_one_case(self, message):
        if 'last' not in self.game:
            return False

        content = message.content

        last_item = self.game['last']['item']
        last_create_time = self.game['last']['create_time']

        answer = last_item['word']
        if message.content != answer:
            # timeout
            if time.time() - last_create_time >= 45 or content == '我要答案':
                reply_content = '很遗憾, {} 的答案是 {}'.format(last_item['emoji'], last_item['word'])
                self.wechat_bot.send_txt_msg(
                    to=message.channel_id,
                    content=reply_content)
                return True
            # tip
            if not self.game['last']['tip']:
                if time.time() - last_create_time >= 20 or content == '提示':
                    # TODO: mark random
                    reply_content = '答案提示 {}'.format(answer[0] + '*' + answer[2] + '*')
                    self.wechat_bot.send_txt_msg(
                        to=message.channel_id,
                        content=reply_content)
                    self.game['last']['tip'] = True
                    return False

            return False

        self.game['winner'][message.sender_id] += 1
        nickname = self.ctx.get_member_nick(message.sender_id)
        reply_content = '恭喜@{} 猜对了, {} 的答案是 {}'.format(
            nickname,
            last_item['emoji'],
            last_item['word'])
        self.wechat_bot.send_txt_msg(
            to=message.channel_id, content=reply_content)
        return True

    def on_next(self, message):
        if not self.game.get('last'):
            return
        success = self.check_one_case(message)
        if success and self.game['items']:
            self.send_one_case(message)
            return

        if not self.game['items']:
            self.set_active(False, message)
            return


class ChengyuLoong(TinyApp):
    APP_NAME = '成语接龙'
    START_WORDS = ('开始成语接龙', '阿邦成语接龙', '阿邦接龙', '阿邦开始成语接龙')
    STOP_WORDS = ('结束游戏', '结束成语接龙')

    def on_app_start(self, message):
        self.game = {}
        self.game['winner'] = defaultdict(int)
        self.game['count'] = 0
        self.game['simple'] = False
        self.game['history'] = []

        word = self.make_one_item()
        self.send_one_case(word, message)

    def on_app_stop(self, message):
        reply_content = '已结束, 本次接龙长度 {} '.format(self.game['count'])
        self.wechat_bot.send_txt_msg(
            to=message.channel_id,
            content=reply_content)

        reply_content = ' -> '.join(self.game['history'])
        self.wechat_bot.send_txt_msg(to=message.channel_id, content=reply_content)
        # TODO: send winner

    def make_one_item(self):
        items = ChengyuDataSource.chengyu_list[:ChengyuDataSource.common_chengyu_count]
        items = filter(lambda item: len(item['words']) == 4, items)
        item = choice(list(items))
        return item['word']

    def send_one_case(self, word, message):
        index = self.game['count'] + 1
        question = '第 {} 条: 「{}」'.format(index, word)
        self.wechat_bot.send_txt_msg(to=message.channel_id, content=question)

        self.game['last'] = word
        self.game['count'] += 1
        self.game['history'].append(word)

    def check_two_word(self, new_word, word):
        if not new_word or len(new_word) != 4:
            return False

        new_item = ChengyuDataSource.chengyu_map.get(new_word)
        item = ChengyuDataSource.chengyu_map.get(word)
        if not new_item or not item:
            return False

        if new_word[0] == word[-1]:
            return True

        first_pinyin = new_item['pinyins'][0]
        last_pinyin = item['pinyins'][-1]

        if first_pinyin == last_pinyin:
            return True

        first_pinyin = ChengyuDataSource.clean_tone(first_pinyin)
        last_pinyin = ChengyuDataSource.clean_tone(last_pinyin)

        if first_pinyin == last_pinyin:
            return True
        return False

    def check_one_case(self, message):
        new_word = message.content
        word = self.game['last']

        # 控制逻辑
        if new_word == '简单模式':
            self.game['simple'] = True
            return None, False
        elif new_word == '关闭简单模式':
            self.game['simple'] = False
            return None, False
        # 提示逻辑
        elif new_word == '提示':
            tip_word = self.find_tip_word(word)
            if not tip_word:
                tip_content = '未找到可用成语'
            else:
                tip_index = choice([1, 2, 3])
                tip_word_chars = list(tip_word)
                for i in range(len(tip_word_chars)):
                    if i not in (0, tip_index):
                        tip_word_chars[i] = ' * '

                tip_content = '提示: 「{}」'.format(''.join(tip_word_chars))

            self.wechat_bot.send_txt_msg(to=message.channel_id, content=tip_content)
            return None, False
        # 排除已使用
        elif new_word in self.game['history']:
            tip_content = '成语「{}」已用过'.format(new_word)
            self.wechat_bot.send_txt_msg(to=message.channel_id, content=tip_content)
            return None, False

        # 严格检查
        ok = self.check_two_word(new_word, word)
        # 补充简单模式
        if not ok and self.game['simple']:
            if len(new_word) >= 3 and new_word[0] == word[-1]:
                ok = True

        if ok:
            nickname = self.ctx.get_member_nick(message.sender_id)
            ok_content = '恭喜@{} 接龙成功 {}'.format(nickname, new_word)
            self.wechat_bot.send_txt_msg(to=message.channel_id, content=ok_content)
            return new_word, True

        # 补充疑问
        if len(new_word) == 4 and new_word not in ChengyuDataSource.chengyu_map:
            not_content = '没有查到「{}」这个成语'.format(new_word)
            self.wechat_bot.send_txt_msg(to=message.channel_id, content=not_content)
            return None, False

        return None, False

    def find_tip_word(self, word):
        tip_words = []
        for tip_word in ChengyuDataSource.chengyu_map:
            if self.check_two_word(tip_word, word):
                tip_words.append(tip_word)
            if len(tip_words) > 15:
                break

        if tip_words:
            return choice(tip_words)

        return None

    def on_next(self, message):
        new_word, success = self.check_one_case(message)
        if success:
            self.send_one_case(new_word, message)


class GameTips(TinyApp):
    APP_NAME = '玩法说明'
    START_WORDS = ('阿邦玩法', '阿邦游戏', '阿邦游戏介绍')

    def on_next(self, message):
        play_descs = [app.play_desc for app in self.ctx.apps]
        reply_content = '\n- - - - - - - - - - - - - - - - -\n'.join([
            f'{i}. {desc}'
            for i, desc in enumerate(filter(None, play_descs))
        ])

        self.wechat_bot.send_txt_msg(
            to=message.channel_id,
            content=reply_content)
        self.set_active(False, message)


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


# use as db
channel_db = {}


def get_channel_ctx(channel_id):
    if channel_id in channel_db:
        return channel_db[channel_id]

    apps = [Hello(), GameTips(), Repeat(), EmojiChengyu(), ChengyuLoong()]

    ctx = ChannelContext(channel_id=channel_id, apps=apps)
    for app in apps:
        app.set_ctx(ctx)

    channel_db[channel_id] = ctx
    return ctx


@app.route('/on_message', methods=['GET', 'POST'])
def on_message():
    body = request.json
    print("body: ", body)
    message = Message(body)

    if message.is_heartbeat:
        return {}

    if not message.channel_id:
        return {}

    ctx = get_channel_ctx(message.channel_id)
    message.set_ctx(ctx)

    for app in ctx.apps:
        if app.need_handle(message):
            app.check_active(message)
            app.check_next(message)

    return {}


if __name__ == '__main__':
    app.run(debug=True)
