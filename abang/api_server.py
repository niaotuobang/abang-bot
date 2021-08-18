# FUCK windows
import _locale
_locale._getdefaultlocale = (lambda *args: ['zh_CN', 'utf8']) # noqa


from flask import Flask
from flask import request

from game import Hello
from game import GameTips
from game import NaiveRepeat
from game import EmojiChengyu
from game import ChengyuLoong
from game import HumanWuGong
from game import SevenSeven
from game import Choice

from core import ChannelContext
from core import Message


app = Flask(__name__)


# use as db
channel_db = {}


def get_channel_ctx(channel_id):
    if channel_id in channel_db:
        return channel_db[channel_id]

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

    ctx = ChannelContext(channel_id=channel_id, apps=apps)
    for app in apps:
        app.set_ctx(ctx)

    channel_db[channel_id] = ctx
    return ctx


@app.route('/on_message', methods=['GET', 'POST'])
def on_message():
    body = request.json
    print("body: ", body)
    message = Message(body)

    if message.is_heartbeat:
        return {}

    if not message.channel_id:
        return {}

    ctx = get_channel_ctx(message.channel_id)
    for app in ctx.apps:
        if app.check_need_handle(message):
            app.check_active(message)
            app.check_next(message)

    return {}


if __name__ == '__main__':
    app.run(debug=True)
