from collections import defaultdict


from flask import Flask
from flask import request

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
        supper().on_flag_change(new_flag)
        if new_flag:
            self.game = {}
            self.game['winner'] = defaultdict(int)

    def next(self, body):
        return None


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
