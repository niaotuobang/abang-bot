import asyncio
import logging

from wechaty import Wechaty
from wechaty.user import Message

from core import ChannelContext, WechatyMessage
from internal import new_channel_ctx


channel_db = {}


def get_channel_ctx(message: WechatyMessage) -> ChannelContext:
    if message.channel_id in channel_db:
        return channel_db[message.channel_id]

    ctx = new_channel_ctx(message.channel_id, message.is_group)
    channel_db[message.channel_id] = ctx
    return ctx


class ABangBot(Wechaty):

    async def on_message(self, msg: Message):
        try:
            await self._on_message(msg)
        except Exception as e:
            logging.error(e, exc_info=True)

    async def _on_message(self, msg: Message):
        """
        listen for message event
        """
        if msg.is_self():
            return
        message: WechatyMessage = WechatyMessage(msg)
        ctx: ChannelContext = get_channel_ctx(message)
        ctx.set_bot(self)

        for app in ctx.apps:
            if app.check_need_handle(message):
                await app.check_active(message)
                await app.check_next(message)


if __name__ == "__main__":
    asyncio.run(ABangBot().start())
