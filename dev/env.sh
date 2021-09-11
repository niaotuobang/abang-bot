#!/bin/bash

# server
export WECHATY_LOG="verbose"
export WECHATY_PUPPET="wechaty-puppet-wechat"
export WECHATY_PUPPET_SERVER_PORT="8077"
export WECHATY_TOKEN="python-wechaty-81ff946e-a3cd-45a5-bb18-b618e8efd75b"

# client
export WECHATY_PUPPET_SERVICE_ENDPOINT=127.0.0.1:$WECHATY_PUPPET_SERVER_PORT
export WECHATY_PUPPET_SERVICE_TOKEN=$WECHATY_TOKEN
