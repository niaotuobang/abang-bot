# FUCK windows
import _locale
_locale._getdefaultlocale = (lambda *args: ['zh_CN', 'utf8'])


import time
from collections import defaultdict


from flask import Flask
from flask import request

from emoji_chengyu.chengyu import gen_one_pair


from wx_sdk import WechatBot
from wx_sdk import RECV_TXT_MSG, HEART_BEAT


app = Flask(__name__)


class TinyApp(object):
    flag = False

    START_WORD = None
    STOP_WORD = None

    wechat_bot = WechatBot()

    def check_flag(self, content):
        if not self.flag and content == self.START_WORD:
            self.flag = True
            self.on_flag_change(self.flag)
        if self.flag and content == self.STOP_WORD:
            self.flag = False
            self.on_flag_change(self.flag)

    def on_flag_change(self, new_flag):
        print(self.__class__.__name__, 'flag change', new_flag)

    def do_next(self, body):
        if not self.flag:
            return
        self.next(body)

    def next(self, body):
        pass


class Repeat(TinyApp):

    START_WORD = '开始复读'
    STOP_WORD = '结束复读'

    def next(self, body):
        self.wechat_bot.send_txt_msg(to=body['id2'], content=body['content'])


class Hello(TinyApp):
    START_WORD = '阿邦'

    def next(self, body):
        self.wechat_bot.send_txt_msg(to=body['id2'], content=u'让我来邦你')
        self.flag = False


class EmojiChengyu(TinyApp):
    START_WORD = '开始表情猜成语'
    STOP_WORD = '结束游戏'

    def on_flag_change(self, new_flag):
        super().on_flag_change(new_flag)
        if new_flag:
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
        N = 100
        pairs = [gen_one_pair() for i in range(N)]
        pairs = list(filter(None, pairs))
        pairs.sort(key=lambda pair: pair['emojis'].count(None))

        self.game['items'] = pairs[:40]

    def send_one_case(self, body):
        if len(self.game['items']) == 0:
            return False
        item = self.game['items'].pop(0)

        question = '题目({}个字): {}'.foramt(len(item['word']), item['emoji'])
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
                    tip_content = '答案提示 {}'.format(answer[0] + '*' * (len(answer) - 1))
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
            first_content = '最多{}个题目,每次问题20秒后提示1个字, 45秒后公布答案'.format(
                len(self.game['items']))
            self.wechat_bot.send_txt_msg(to=body['id2'], content=first_content)
            # send first question
            self.send_one_case(body)
        else:
            ok = self.check_one_case(body)
            if ok and self.flag:
                self.send_one_case(body)


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
        content = body['content']
        for app in config['apps']:
            app.check_flag(content)
            app.do_next(body)

    return {}


if __name__ == '__main__':
    app.run(debug=True)
