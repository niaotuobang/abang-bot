from random import choice

from emoji_chengyu.puzzle import gen_puzzle
from emoji_chengyu.data import ChengyuItem
from emoji_chengyu.data import common_chengyu_list
from emoji_chengyu.data import DefaultChengyuManager


def choice_common_chengyu() -> ChengyuItem:
    item = choice(common_chengyu_list)
    return item
