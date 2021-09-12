from collections import Counter
from functools import cached_property
import random
from random import choice
import re
import time
import datetime
import itertools

from wechaty_puppet import MessageType

from emoji_chengyu.puzzle import gen_puzzle
from emoji_chengyu.data import common_chengyu_list
from emoji_chengyu.data import DefaultChengyuManager
import pypinyin

from core import GameData
from core import ChannelContext, WechatyMessage

def is_pinyin_equal(wordA, wordB, strict=False):
    assert len(wordA) == 1
    assert len(wordB) == 1
    if wordA == wordB:
        return True

    style = pypinyin.Style.TONE if strict else pypinyin.Style.NORMAL

    pinyinsA = pypinyin.pinyin(wordA, style=style)
    pinyinsB = pypinyin.pinyin(wordB, style=style)
    if set(pinyinsA[0]) & set(pinyinsB[0]):
        return True

    return False


def choice_common_chengyu():
    item = choice(common_chengyu_list)
    return item.word


class TinyApp(object):
    active = False

    MESSAGE_TYPES = (MessageType.MESSAGE_TYPE_TEXT,)

    APP_NAME = None
    APP_DESC = None
    START_WORDS = ()
    STOP_WORDS = ()

    NEXT_LINE = '- - - - - - - - - - - - - - - -'

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

    def check_need_handle(self, message):
        if message.msg_type in self.MESSAGE_TYPES:
            return True
        return False

    def check_is_start(self, message):
        return message.content in self.START_WORDS

    def check_is_stop(self, message):
        return message.content in self.STOP_WORDS

    def check_active(self, message):
        if self.check_is_start(message):
            self.set_active(True, message)
        elif self.check_is_stop(message):
            self.set_active(False, message)

    async def check_next(self, message):
        if self.active:
            await self.on_app_next(message)

    def set_active(self, active, message):
        if self.active == active:
            return
        print(self.__class__.__name__, ' self.active, active ', self.active, active)
        self.active = active
        if self.active:
            self.on_app_start(message)
        else:
            self.on_app_stop(message)

    async def on_app_start(self, message):
        pass

    async def on_app_stop(self, message):
        pass

    async def on_app_next(self, message):
        pass


class WinnerMixin(object):

    WIN_TOP = 3

    def start_record_winner(self):
        self.winner = GameData()
        self._record = True

    def stop_record_winner(self):
        self._record = False
        self._collect_ctx()
        self.winner = None

    def _collect_ctx(self):
        app_name = self.__class__.__name__
        counter = Counter(self.winner)
        for _, item in enumerate(counter.most_common(self.WIN_TOP)):
            self.ctx.collect_winner(app_name, wx_id=item[0])

    def record_winner(self, wx_id):
        if not self._record:
            return
        self.winner[wx_id] = self.winner.get(wx_id, 0) + 1

    def make_winner_content(self):
        medals = ['🏅', '🥈', '🥉']

        contents = []
        counter = Counter(self.winner)
        for index, item in enumerate(counter.most_common(self.WIN_TOP)):
            winner_id = item[0]
            count = item[1]
            nickname = self.ctx.get_member_nick(winner_id)
            content = f'{medals[index]} 第 {index + 1} 名: @{nickname} (赢了 {count} 次)'
            contents.append(content)

        reply_content = '\n'.join(contents)
        return reply_content

    def send_winners(self):
        reply_content = self.make_winner_content()
        self.ctx.reply(reply_content)


class Hello(TinyApp):
    APP_NAME = '打招呼'
    START_WORDS = ('阿邦', '毛毛', '阿邦你好', '邦邦')

    async def on_app_next(self, message: WechatyMessage):
        reply_content = '让我来邦你'
        await self.ctx.say(reply_content)
        self.set_active(False, message)


class NaiveRepeat(TinyApp):

    APP_NAME = '复读机'
    START_WORDS = ('开始复读', '阿邦复读', '阿邦开始复读')
    STOP_WORDS = ('结束复读', '别复读了')

    STUPID_MODE = '弱智复读'
    RANDOM_MODE = '随机复读'
    CLEVER_MODE = '智能复读'

    MODES = (STUPID_MODE, RANDOM_MODE, CLEVER_MODE)
    APP_DESC = f"输入 {'、'.join(MODES)} 切换模式"
    RANDOM_RATIO = 0.1
    HISTORY_CONTENT_LEN = 10

    def on_app_start(self, _):
        self.game = {}
        self.game['history'] = []
        self.game['mode'] = self.MODES[0]

    def on_app_next(self, message):
        content = message.content
        if message.content in self.MODES:
            self.game['mode'] = content
            return

        self.game['history'].append(content)
        self.game['history'] = self.game['history'][-self.HISTORY_CONTENT_LEN:]

        repeat = False
        if self.game['mode'] == self.STUPID_MODE:
            repeat = True
        elif self.game['mode'] == self.RANDOM_MODE:
            if random.random() < self.RANDOM_RATIO:
                repeat = True
        elif self.game['mode'] == '智能复读':
            if self.game['history'].count(content) > 1:
                repeat = True

        if repeat:
            self.ctx.reply(message.content)


class EmojiChengyu(TinyApp, WinnerMixin):
    APP_NAME = '表情猜成语'
    START_WORDS = ('开始表情猜成语', '阿邦表情猜成语', '阿邦表情成语', '开始抽象成语')
    STOP_WORDS = ('结束游戏', '结束表情猜成语')

    def on_app_start(self, _):
        self.start_record_winner()
        self.game = {}
        self.game['items'] = []
        self.game['checked'] = []
        self.game['last'] = None
        self.game['index'] = 0
        self.make_more_item()

        first_content = '最多{}个题目,每次问题20秒后提示1个字(也可发送"提示"触发), 45秒后公布答案(也可发送"我要答案"触发)'.format(
            len(self.game['items']))
        self.ctx.reply(first_content)

        self.send_one_case()

    def on_app_stop(self, _):
        self.game = {}
        self.send_winners()
        self.stop_record_winner()

    def make_more_item(self):
        N = 60
        pairs = gen_puzzle()
        pairs = filter(None, pairs)
        pairs = filter(lambda pair: len(pair['words']) == 4, pairs)
        pairs = itertools.islice(pairs, 0, N)
        pairs = list(pairs)
        pairs.sort(key=lambda pair: pair['emojis'].count(None))

        pairs2 = []
        used_words = {}
        for pair in pairs:
            if pair['word'] not in used_words:
                pairs2.append(pair)
                used_words[pair['word']] = True

        self.game['items'] = pairs2[:20]

    def send_one_case(self):
        if len(self.game['items']) == 0:
            return False

        item = self.game['items'].pop(0)
        self.game['index'] += 1

        question = '第{} 题 ({}个字): {}'.format(
            self.game['index'],
            len(item['word']),
            item['emoji'])

        self.ctx.reply(question)

        self.game['last'] = {
            'item': item,
            'create_time': time.time(),
            'tip': False,
        }

        print(item['word'], item['emoji'])
        return True

    def check_one_case(self, message):
        # TODO: clean this.
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
                self.ctx.reply(reply_content)
                return True
            # tip
            if not self.game['last']['tip']:
                if time.time() - last_create_time >= 20 or content == '提示':
                    # TODO: mark random
                    reply_content = '答案提示 {}'.format(answer[0] + '*' + answer[2] + '*')
                    self.ctx.reply(reply_content)
                    self.game['last']['tip'] = True
                    return False

            return False

        self.record_winner(message.sender_id)
        reply_content = '恭喜你猜对了, {} 的答案是 {}'.format(
            last_item['emoji'],
            last_item['word'])

        self.ctx.reply_at(reply_content, message.sender_id)
        return True

    def on_app_next(self, message):
        if not self.game.get('last'):
            return
        success = self.check_one_case(message)
        if success and self.game['items']:
            self.send_one_case()
            return

        if not self.game['items']:
            self.set_active(False, message)
            return


class ChengyuLoong(TinyApp, WinnerMixin):
    APP_NAME = '成语接龙'
    START_WORDS = ('开始成语接龙', '阿邦成语接龙', '阿邦接龙', '阿邦开始成语接龙')
    STOP_WORDS = ('结束游戏', '结束成语接龙')
    TIPS = '提示'
    THIS_QUESTION = '当前接龙'
    APP_DESC = f'输入 {TIPS} 可提示,输入 {THIS_QUESTION} 显示正在接龙的词'

    def on_app_start(self, message):
        self.start_record_winner()

        self.game = {}
        self.game['count'] = 0
        self.game['history'] = []

        new_word = choice_common_chengyu()
        self.send_one_case(new_word)

    def on_app_stop(self, message):
        reply_content = '已结束, 本次接龙长度 {}'.format(self.game['count'])
        self.ctx.reply(reply_content)

        reply_content = ' -> '.join(self.game['history'])
        self.ctx.reply(reply_content)

        self.send_winners()
        self.stop_record_winner()

    def send_one_case(self, word):
        index = self.game['count'] + 1
        question = '第 {} 条: 「{}」'.format(index, word)
        self.ctx.reply(question)

        self.game['last'] = word
        self.game['count'] += 1
        self.game['history'].append(word)

    def resend_case(self):
        word = self.game['last']
        index = self.game['count']
        question = '第 {} 条: 「{}」'.format(index, word)
        self.ctx.reply(question)

    def is_match(self, old_word, new_word):
        if len(new_word) < 3:
            return False
        equal = is_pinyin_equal(old_word[-1], new_word[0])
        if not equal:
            return False

        item = DefaultChengyuManager.get_by_word(new_word)
        if item:
            return True
        return False

    def check_match(self, message):
        old_word = self.game['last']
        new_word = message.content

        if not self.is_match(old_word, new_word):
            return False

        if new_word in self.game['history']:
            tip_content = '「{}」已用过'.format(new_word)
            self.ctx.reply(tip_content)
            return False

        return True

    def on_matched(self, message):
        self.record_winner(message.sender_id)

        reply_content = '恭喜接龙成功 --> {}'.format(message.content)
        self.ctx.reply_at(reply_content, message.sender_id)

    def find_tip_word(self, old_word) -> str:
        tip_words = []
        for item in DefaultChengyuManager.chengyu_list:
            tip_word: str = item.word
            if self.is_match(old_word, tip_word):
                if tip_word not in self.game['history']:
                    tip_words.append(tip_word)

            if len(tip_words) > 15:
                break

        if not tip_words:
            return None
        return choice(tip_words)

    def send_tip_word(self):
        old_word = self.game['last']
        tip_word = self.find_tip_word(old_word)
        if tip_word:
            keys = list(tip_word)
            mask_indexes = random.sample([1, 2, 3], 2)
            for i in range(len(keys)):
                if i in mask_indexes:
                    keys[i] = ' * '

            tip_content = f"提示: 「{''.join(keys)}」"
        else:
            tip_content = '未找到可用成语'

        self.ctx.reply(tip_content)

    def on_app_next(self, message):
        content = message.content
        if content == self.THIS_QUESTION:
            self.resend_case()
        elif content == self.TIPS:
            self.send_tip_word()
        else:
            if self.check_match(message):
                self.on_matched(message)
                self.send_one_case(content)


class HumanWuGong(ChengyuLoong):
    APP_NAME = '俗语接龙(人体蜈蚣)'
    START_WORDS = ('开始俗语接龙', '开始人体蜈蚣')
    STOP_WORDS = ('结束游戏', '结束俗语接龙', '结束人体蜈蚣')

    THIS_QUESTION = '当前接龙'
    APP_DESC = f'输入 {THIS_QUESTION} 显示正在接龙的词'

    def is_match(self, old_word, new_word):
        old_word = self.game['last']
        equal = is_pinyin_equal(old_word[-1], new_word[0])
        if not equal:
            return False
        return True

    def on_app_next(self, message):
        content = message.content
        if content == self.THIS_QUESTION:
            self.resend_case()
            return

        if self.check_match(message):
            self.on_matched(message)
            self.send_one_case(content)


class GameTips(TinyApp):
    APP_NAME = '玩法说明'
    START_WORDS = ('阿邦玩法', '阿邦游戏', '阿邦游戏介绍')

    def on_app_next(self, message):
        play_descs = [app.play_desc for app in self.ctx.apps]
        sep_line = f'\n{self.NEXT_LINE}\n'
        reply_content = sep_line.join([
            f'{i}. {desc}'
            for i, desc in enumerate(filter(None, play_descs))
        ])

        self.ctx.reply(reply_content)

        self.set_active(False, message)


class SevenSeven(TinyApp):
    APP_NAME = '七夕限定抽奖活动'
    START_WORDS = ('七夕抽奖活动开始',)
    STOP_WORDS = ('七夕抽奖活动正式结束',)
    GIFT_WORD = '七夕抽奖'
    GIFT_REGEX = re.compile(r'^七夕抽奖我要一杯(\w+)奶茶$')
    EXCLUDE_WX_NAMES = ('阿邦', '刘二狗🍑')
    VALID_DAYS = ('2021-08-14',)

    def check_active(self, message):
        if not message.is_group:
            return
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        if today not in self.VALID_DAYS:
            return

        super().check_active(message)

    def on_app_start(self, message):
        self.game = {}

        reply_content = '''默认全员参加,抽中了奶茶但是对方不愿付款的可以找管委会(苏哥陶陶大王文君)领一杯蜜雪冰城。\n- - - - - - - - - - - -\n抽奖规则: 发送 七夕抽奖 或 七夕抽奖我要一杯XX奶茶 即可参与抽奖，即时开奖。兑奖时间截止七夕当晚22点。'''
        self.ctx.reply(reply_content)

        member_ids = self.ctx.get_channel_member_ids()
        # 排除机器人
        member_ids2 = []
        for member_id in member_ids:
            nickname = self.ctx.get_member_nick(member_id)
            if nickname not in self.EXCLUDE_WX_NAMES:
                member_ids2.append(member_id)

        self.game['member_ids'] = member_ids2
        self.game['matched'] = {}

        reply_content = f'活动已开始, 共{len(self.game["member_ids"])}人参加, 大家快开始参与吧'
        self.ctx.reply(reply_content)

    def on_app_stop(self, _):
        self.send_matched_info()

        reply_content = '''抽奖活动已结束, 感谢大家度过了愉悦的一天'''
        self.ctx.reply(reply_content)

    def send_matched_info(self):
        reply_contents = ['抽奖进度', f'共{len(self.game["matched"])}人抽中', '- - - - - - - - - - - -']
        for wx_id in self.game['matched']:
            reply_contents.append(self.get_matched_content(wx_id))
        reply_content = '\n'.join(reply_contents)

        self.ctx.reply(reply_content)

    def get_matched_content(self, wx_id):
        if wx_id not in self.game['matched']:
            return None

        gift = self.game['matched'][wx_id]
        giver_id, gift_content = gift
        getter = self.ctx.get_member_nick(wx_id)
        giver = self.ctx.get_member_nick(giver_id)
        reply_content = f'@{getter} 抽中 @{giver} 送出的 一杯{gift_content}'
        return reply_content

    def check_new_case(self, message, gift_content):
        if message.sender_id in self.game['matched']:
            reply_content = '您已参与抽奖 ' + self.get_matched_content(message.sender_id)
            self.ctx.reply(reply_content)
            return

        valid_member_ids = list(self.game['member_ids'])
        if message.sender_id in valid_member_ids:
            valid_member_ids.remove(message.sender_id)

        if not valid_member_ids:
            reply_content = '非常抱歉, 你来晚了, 现在已无可抽奖对象, 快去找一个现实中的人吧'
            self.ctx.reply(reply_content)
            return

        giver_id = choice(valid_member_ids)
        self.game['matched'][message.sender_id] = (giver_id, gift_content)
        # update
        member_ids = list(set(self.game['member_ids']) - set([giver_id]))
        self.game['member_ids'] = member_ids

        reply_content = '恭喜 ' + self.get_matched_content(message.sender_id)
        self.ctx.reply_at(reply_content, message.sender_id)
        return

    def on_app_next(self, message):
        content = message.content
        if content == self.GIFT_WORD:
            self.check_new_case(message, '奶茶')
            return

        gifts = self.GIFT_REGEX.findall(content)
        if gifts:
            gift_content = gifts[0]
            self.check_new_case(message, gift_content)
            return

        if content == '抽奖进度':
            self.send_matched_info()


class Choice(TinyApp):
    APP_NAME = '抽奖'
    APP_DESC = '输入「抽N个人xxx」进行抽奖'
    CHOICE_RE = re.compile(r'抽([\t\d ]+)个?人(\w+)?')

    def check_is_start(self, message):
        return bool(self.CHOICE_RE.search(message.content))

    def parse_N_and_XX(self, message):
        match = self.CHOICE_RE.search(message.content)
        N, XX = match.groups()
        N = N.replace(' ', '').replace('\t', '').strip()
        XX = XX.strip() if XX else ''
        return int(N), XX

    def on_app_next(self, message):
        N, XX = self.parse_N_and_XX(message)
        member_ids = self.ctx.get_channel_member_ids()
        if len(member_ids) < N:
            self.ctx.reply_at('抽奖人数超过群聊人数, 请重新输出', message.sender_id)
            return

        member_ids2 = random.sample(member_ids, N)

        sender = self.ctx.get_member_nick(message.sender_id)
        reply_contents = [
            f'@{sender} 发起的抽奖结果公示',
            f'抽奖详情: {N}人, {XX}',
            self.NEXT_LINE,
        ]

        for wx_id in member_ids2:
            nickname = self.ctx.get_member_nick(wx_id)
            reply_contents.append(f'@{nickname}')

        reply_content = '\n'.join(reply_contents)
        self.ctx.reply(reply_content)

        self.set_active(False, message)


class Rank(TinyApp):
    APP_NAME = '排行榜'
    LAZY_RANK = '闲人排行榜'
    REPEAT_RANK = '复读机排行榜'
    GOLD_RANK = '金句排行榜'
    START_WORDS = (LAZY_RANK, REPEAT_RANK, GOLD_RANK)

    def on_app_next(self, message):
        content = message.content
        if content == self.LAZY_RANK:
            pass
        self.set_active(False, message)
