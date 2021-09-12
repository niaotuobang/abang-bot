import asyncio
from typing import List, Optional, Union

from wechaty_puppet import FileBox  # type: ignore

from wechaty import Wechaty, Contact
from wechaty.user import Message, Room

from core import ChannelContext, WechatyMessage
from internal import new_channel_ctx


channel_db = {}


def get_channel_ctx(channel_id: str) -> ChannelContext:
    if channel_id not in channel_db:
        return channel_db[channel_id]

    ctx = new_channel_ctx(channel_id)
    channel_db[channel_id] = ctx
    return ctx


class ABangBot(Wechaty):

    async def on_message(self, msg: Message):
        """
        listen for message event
        """
        message: WechatyMessage = WechatyMessage(msg)
        ctx: ChannelContext = get_channel_ctx(message.channel_id)
        for app in ctx.apps:
            if app.check_need_handle(message):
                app.check_active(message)
                app.check_next(message)


if __name__ == "__main__":
    asyncio.run(ABangBot().start())
