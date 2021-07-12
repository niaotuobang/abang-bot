from flask import Flask
from flask import request

from wx_sdk import WechatBot
from wx_sdk import RECV_TXT_MSG


app = Flask(__name__)


wechat_bot = WechatBot()


@app.route('/on_message'， methods=['GET', 'POST'])
def on_message():
    body = request.json

    if body['type'] == RECV_TXT_MSG:
        if u'阿邦' in body['content']:
            wechat_bot.send_txt_msg(to=body['id2'], content=u'让我来邦你')
        if u'毛毛' in body['content']:
            wechat_bot.send_txt_msg(to=body['id2'], content=u'毛毛来了')

    return {}


if __name__ == '__main__':
    app.run(debug=True)
