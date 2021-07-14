# FUCK windows
import _locale
_locale._getdefaultlocale = (lambda *args: ['zh_CN', 'utf8'])


import time
from collections import defaultdict
from random import choice

from flask import Flask
from flask import request

from emoji_chengyu.chengyu import gen_one_emoji_pair
from emoji_chengyu.data import DataSource as ChengyuDataSource

from wx_sdk import WechatBot
from wx_sdk import RECV_TXT_MSG, HEART_BEAT


app = Flask(__name__)


class TinyApp(object):
    active = False

    START_WORDS = ()
    STOP_WORDS = ()

    wechat_bot = WechatBot()

    def check_active(self, body):
        content = body['content']
        if content in self.START_WORDS:
            self.set_active(True, body)
        elif content in self.STOP_WORDS:
            self.set_active(False, body)

    def set_active(self, active, body):
        if self.active == active:
            return

        print(self.__class__.__name__, ' self.active, active ', self.active, active)
        self.active = active
        if self.active:
            self.on_app_start(body)
        else:
            self.on_app_stop(body)

    def on_app_start(self, body):
        pass

    def on_app_stop(self, body):
        pass

    def check_next(self, body):
        if self.active:
            self.on_next(body)

    def on_next(self, body):
        pass


class Hello(TinyApp):
    START_WORDS = ('阿邦', '毛毛')

    def on_next(self, body):
        self.wechat_bot.send_txt_msg(to=body['id2'], content=u'让我来邦你')
        self.set_active(False, body)


class Repeat(TinyApp):

    START_WORDS = ('开始复读',)
    STOP_WORDS = ('结束复读',)

    def on_next(self, body):
        self.wechat_bot.send_txt_msg(to=body['id2'], content=body['content'])


class EmojiChengyu(TinyApp):
    START_WORDS = ('开始表情猜成语',)
    STOP_WORDS = ('结束游戏', '结束表情猜成语')

    def on_app_start(self, body):
        self.game = {}
        self.game['winner'] = defaultdict(int)
        self.game['items'] = []
        self.game['checked'] = []
        self.game['last'] = None
        self.make_more_item()

        first_content = '最多{}个题目,每次问题20秒后提示1个字(也可发送"提示"触发), ' + \
            '45秒后公布答案(也可发送"我要答案"触发)'.format(len(self.game['items']))
        self.wechat_bot.send_txt_msg(to=body['id2'], content=first_content)
        self.send_one_case(body)

    def on_app_stop(self, body):
        # TODO: send the winner
        self.game = {}

    def make_more_item(self):
        N = 50
        pairs = [gen_one_emoji_pair(search_count=500) for i in range(N)]
        pairs = filter(None, pairs)
        pairs = filter(lambda pair: len(pair['words']) == 4, pairs)
        pairs = list(pairs)
        pairs.sort(key=lambda pair: pair['emojis'].count(None))
        # TODO: 按文字去重

        self.game['items'] = pairs[:30]

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

    def on_next(self, body):
        if not self.game.get('last'):
            return
        success = self.check_one_case(body)
        # 最后一个
        if not self.game['items']:
            self.set_active(False, body)
            return
        elif success:
            self.send_one_case(body)


class ChengyuLoong(TinyApp):

    START_WORDS = ('开始成语接龙',)
    STOP_WORDS = ('结束游戏', '结束成语接龙')

    def on_app_start(self, body):
        self.game = {}
        self.game['winner'] = defaultdict(int)
        self.game['count'] = 0

        word = self.make_one_item()
        self.send_one_case(word, body)

    def on_app_stop(self, body):
        content = '已结束, 本次接龙长度 {}'.foramt(self.game['count'])
        self.wechat_bot.send_txt_msg(to=body['id2'], content=content)

    def make_one_item(self):
        items = ChengyuDataSource.chengyu_list[:ChengyuDataSource.common_chengyu_count]
        items = filter(lambda item: len(item['words']) == 4, items)
        item = choice(list(items))
        return item['word']

    def send_one_case(self, word, body):
        index = self.game['count'] + 1
        question = '第 {} 条: 「{}」'.format(index, word)
        self.wechat_bot.send_txt_msg(to=body['id2'], content=question)

        self.game['last'] = word
        self.game['count'] += 1

    def check_two_word(new_word, word):
        if not new_word or len(new_word) != 4:
            return False

        if new_word[0] == word[-1]:
            return True

        new_item = ChengyuDataSource.chengyu_map.get(new_word)
        item = ChengyuDataSource.chengyu_map.get(word)
        if not new_item or not item:
            return False

        first_pinyin = new_item['pinyins'][0]
        last_pinyin = item['pinyins'][-1]

        if first_pinyin == last_pinyin:
            return True

        first_pinyin = ChengyuDataSource.clean_tone(first_pinyin)
        last_pinyin = ChengyuDataSource.clean_tone(last_pinyin)

        if first_pinyin == last_pinyin:
            return True
        return False

    def check_one_case(self, body):
        new_word = body['content']
        word = self.game['last']

        if not new_word or len(new_word) != 4:
            return None, False

        # 提示逻辑
        if new_word == '提示':
            tip_words = []
            for tip_word in ChengyuDataSource.chengyu_map:
                if self.check_two_word(tip_word, word):
                    tip_words.append(tip_word)
                if len(tip_word) > 5:
                    break
            if not tip_words:
                tip_content = '未找到可用成语'
            else:
                tip_word = choice(tip_words)
                tip_content = '提示: {} * {} *'.format(tip_word[0], tip_word[2])

            self.wechat_bot.send_txt_msg(to=body['id2'], content=tip_content)
            return None, False



        if new_word not in ChengyuDataSource.chengyu_map:
            not_content = '抱歉没查到「{}」这个成语'.format(new_word)
            self.wechat_bot.send_txt_msg(to=body['id2'], content=not_content)
            return None, False

        ok = self.check_two_word(new_word, word)
        if ok:
            ok_content = '恭喜接龙成功 {}'.format(new_word)
            self.wechat_bot.send_txt_msg(to=body['id2'], content=ok_content)
            return new_word, True
        return None, False

    def on_next(self, body):
        new_word, success = self.check_one_case(body)
        if success:
            self.send_one_case(new_word, body)


channel_config = {}


@app.route('/on_message', methods=['GET', 'POST'])
def on_message():
    body = request.json

    if body['type'] == HEART_BEAT:
        return {}

    if 'id2' not in body:
        return {}

    channel_id = body['id2']
    if channel_id not in channel_config:
        channel_config[channel_id] = {'apps': [Repeat(), Hello(), EmojiChengyu(), ChengyuLoong()]}

    config = channel_config[channel_id]
    if body['type'] == RECV_TXT_MSG:
        for app in config['apps']:
            app.check_active(body)
            app.check_next(body)

    return {}


if __name__ == '__main__':
    app.run(debug=True)
