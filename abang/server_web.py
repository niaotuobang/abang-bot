import asyncio
from typing import List, Optional, Union

from wechaty_puppet import FileBox  # type: ignore

from wechaty import Wechaty, Contact
from wechaty.user import Message, Room


from internal import new_channel_ctx


channel_db = {}


def get_channel_ctx(channel_id):
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
        msg.room

        from_contact: Optional[Contact] = msg.talker()
        text = msg.text()
        room: Optional[Room] = msg.room()
        mini_msg = msg.to_mini_program()
        await mini_msg
        print(mini_msg)
        print(mini_msg.to_json())
        if text == 'ding':
            conversation: Union[
                Room, Contact] = from_contact if room is None else room
            await conversation.ready()
            await conversation.say('dong')
            file_box = FileBox.from_url(
                'https://ss3.bdstatic.com/70cFv8Sh_Q1YnxGkpoWK1HF6hhy/it/'
                'u=1116676390,2305043183&fm=26&gp=0.jpg',
                name='ding-dong.jpg')
            await conversation.say(file_box)


asyncio.run(ABangBot().start())
