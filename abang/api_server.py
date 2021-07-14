# FUCK windows
import _locale
_locale._getdefaultlocale = (lambda *args: ['zh_CN', 'utf8'])


import time
from collections import defaultdict
from random import choice

from flask import Flask
from flask import request

from emoji_chengyu.chengyu import gen_one_pair
from emoji_chengyu.data import DataSource as ChengyuDataSource

from wx_sdk import WechatBot
from wx_sdk import RECV_TXT_MSG, HEART_BEAT


app = Flask(__name__)


class TinyApp(object):
    flag = False

    START_WORDS = None
    STOP_WORDS = None

    wechat_bot = WechatBot()

    def check_flag(self, body):
        content = body['content']
        if self.START_WORDS:
            if not self.flag and content in self.START_WORDS:
                self.flag = True
                print(self.__class__.__name__, 'flag change', self.flag)
                self.on_flag_change(self.flag)

        if self.STOP_WORDS:
            if self.flag and content in self.STOP_WORDS:
                self.flag = False
                print(self.__class__.__name__, 'flag change', self.flag)
                self.on_flag_change(self.flag)

    def on_flag_change(self, body):
        pass

    def do_next(self, body):
        if not self.flag:
            return
        self.next(body)

    def next(self, body):
        pass


class Repeat(TinyApp):

    START_WORDS = ('开始复读',)
    STOP_WORDS = ('结束复读',)

    def next(self, body):
        self.wechat_bot.send_txt_msg(to=body['id2'], content=body['content'])


class Hello(TinyApp):
    START_WORDS = ('阿邦', '毛毛')

    def next(self, body):
        self.wechat_bot.send_txt_msg(to=body['id2'], content=u'让我来邦你')
        self.flag = False


class EmojiChengyu(TinyApp):
    START_WORDS = ('开始表情猜成语',)
    STOP_WORDS = ('结束游戏', '结束表情猜成语')

    def on_flag_change(self, body):
        if self.flag:
            self.game = {}
            self.game['winner'] = defaultdict(int)
            self.game['items'] = []
            self.game['checked'] = []
            self.game['last'] = None
            self.make_more_item()
        else:
            # TODO: send the winner
            self.game = {}

    def make_more_item(self):
        N = 50
        pairs = [gen_one_pair(search_count=500) for i in range(N)]
        pairs = filter(None, pairs)
        pairs = filter(lambda pair: len(pair['words']) == 4, pairs)
        pairs = list(pairs)
        pairs.sort(key=lambda pair: pair['emojis'].count(None))

        self.game['items'] = pairs[:20]

    def send_one_case(self, body):
        if len(self.game['items']) == 0:
            return False
        item = self.game['items'].pop(0)

        question = '题目({}个字): {}'.format(len(item['word']), item['emoji'])
        self.wechat_bot.send_txt_msg(to=body['id2'], content=question)
        self.game['last'] = {
            'item': item,
            'create_time': time.time(),
            'tip': False,
        }

        print(item['word'], item['emoji'])
        return True

    def check_one_case(self, body):
        if 'last' not in self.game:
            return False

        last_item = self.game['last']['item']
        last_create_time = self.game['last']['create_time']

        content = body['content']
        answer = last_item['word']
        if content != answer:
            # timeout
            if time.time() - last_create_time >= 45 or content == '我要答案':
                reply_content = '很遗憾, {} 的答案是 {}'.format(last_item['emoji'], last_item['word'])
                self.wechat_bot.send_txt_msg(to=body['id2'], content=reply_content)
                return True
            # tip
            if not self.game['last']['tip']:
                if time.time() - last_create_time >= 20 or content == '提示':
                    tip_content = '答案提示 {}'.format(answer[0] + '*' + answer[2] + '*')
                    self.wechat_bot.send_txt_msg(to=body['id2'], content=tip_content)
                    self.game['last']['tip'] = True
                    return False

            return False

        self.game['winner'][body['id1']] += 1
        reply_content = '恭喜猜对了, {} 的答案是 {}'.format(last_item['emoji'], last_item['word'])
        self.wechat_bot.send_txt_msg(to=body['id2'], content=reply_content)
        return True

    def next(self, body):
        if self.game.get('last') is None:
            first_content = '最多{}个题目,每次问题20秒后提示1个字(也可发送"提示"触发), 45秒后公布答案(也可发送"我要答案"触发)'.format(
                len(self.game['items']))
            self.wechat_bot.send_txt_msg(to=body['id2'], content=first_content)
            # send first question
            self.send_one_case(body)
        else:
            ok = self.check_one_case(body)
            if ok and self.flag:
                self.send_one_case(body)


class ChengyuList(TinyApp):
    def on_flag_change(self, body):
        if self.flag:
            self.game = {}
            self.game['winner'] = defaultdict(int)
            self.game['last'] = self.make_one_item()
        else:
            self.game = {}

    def make_one_item():
        items = ChengyuDataSource.chengyu_list[:len(ChengyuDataSource.chengyu_count_map)]
        return choice(items)

    def next(self, body):
        pass


channel_config = {}


@app.route('/on_message', methods=['GET', 'POST'])
def on_message():
    body = request.json

    if body['type'] == HEART_BEAT:
        return {}

    channel_id = body['id2']
    if channel_id not in channel_config:
        channel_config[channel_id] = {'apps': [Repeat(), Hello(), EmojiChengyu()]}

    config = channel_config[channel_id]
    if body['type'] == RECV_TXT_MSG:
        for app in config['apps']:
            app.check_flag(body)
            app.do_next(body)

    return {}


if __name__ == '__main__':
    app.run(debug=True)
