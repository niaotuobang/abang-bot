from game import Hello
from game import GameTips
from game import NaiveRepeat
from game import EmojiChengyu
from game import ChengyuLoong
from game import HumanWuGong
from game import SevenSeven
from game import Choice


from core import ChannelContext


def new_channel_ctx(channel_id: str, is_group: bool) -> ChannelContext:
    apps = [
        Hello(),
        GameTips(),
        NaiveRepeat(),
        EmojiChengyu(),
        ChengyuLoong(),
        HumanWuGong(),
        SevenSeven(),
        Choice(),
    ]

    ctx = ChannelContext(channel_id=channel_id, is_group=is_group, apps=apps)
    for app in apps:
        app.set_ctx(ctx)

    return ctx
