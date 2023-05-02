# coding:utf-8

import sys
import io
import os
import time
import re
import json
import base64
import threading

sys.path.append(os.getcwd() + "/class/core")
import mw

import telebot


def getPluginName():
    return 'tgbot'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


sys.path.append(getServerDir() + "/extend")


def getConfigData():
    cfg_path = getServerDir() + "/data.cfg"
    if not os.path.exists(cfg_path):
        mw.writeFile(cfg_path, '{}')
    t = mw.readFile(cfg_path)
    return json.loads(t)


def writeConf(data):
    cfg_path = getServerDir() + "/data.cfg"
    mw.writeFile(cfg_path, json.dumps(data))
    return True


def getExtCfg():
    cfg_path = getServerDir() + "/extend.cfg"
    if not os.path.exists(cfg_path):
        mw.writeFile(cfg_path, '{}')
    t = mw.readFile(cfg_path)
    return json.loads(t)


def getStartExtCfgByTag(tag='push'):
    # 获取开启的扩展
    elist = getExtCfg()
    rlist = []
    for x in elist:
        if x['tag'] == tag and x['status'] == 'start':
            rlist.append(x)
    return rlist


def writeLog(log_str):
    if __name__ == "__main__":
        print(log_str)

    now = mw.getDateFromNow()
    log_file = getServerDir() + '/task.log'
    mw.writeFileLog(now + ':' + log_str, log_file, limit_size=5 * 1024)
    return True

# start tgbot
cfg = getConfigData()
while True:
    cfg = getConfigData()
    if 'bot' in cfg and 'app_token' in cfg['bot']:
        if cfg['bot']['app_token'] != '' and cfg['bot']['app_token'] != 'app_token':
            break
    writeLog('等待输入配置,填写app_token')
    time.sleep(3)


bot = telebot.TeleBot(cfg['bot']['app_token'])


init_list = getStartExtCfgByTag('init')
for p in init_list:
    try:
        script = p['name'].split('.')[0]
        __import__(script).init(bot)
    except Exception as e:
        writeLog('-----init error start -------')
        writeLog(mw.getTracebackInfo())
        writeLog('-----init error end -------')

# @bot.message_handler(commands=['start', 'help'])
# def hanle_start_help(message):
#     bot.reply_to(message, "hello world")


# @bot.message_handler(commands=['mw_echo'])
# def hanle_mw_echo(message):
#     bot.reply_to(message, message.text)


@bot.message_handler(commands=['chat_id'])
def hanle_get_chat_id(message):
    bot.reply_to(message, message.chat.id)


@bot.message_handler(func=lambda message: True)
def all_message(message):
    rlist = getStartExtCfgByTag('receive')
    for r in rlist:
        try:
            script = r['name'].split('.')[0]
            __import__(script).run(bot, message)
        except Exception as e:
            writeLog('-----all_message error start -------')
            writeLog(mw.getTracebackInfo())
            writeLog('-----all_message error end -------')


@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    rlist = getStartExtCfgByTag('receive')
    for r in rlist:
        try:
            script = r['name'].split('.')[0]
            __import__(script).answer_callback_query(bot, call)
        except Exception as e:
            writeLog('-----callback_query_handler error start -------')
            writeLog(mw.getTracebackInfo())
            writeLog('-----callback_query_handler error end -------')


def runBotPushTask():
    plist = getStartExtCfgByTag('push')
    for p in plist:
        try:
            script = p['name'].split('.')[0]
            __import__(script).run(bot)
        except Exception as e:
            writeLog('-----runBotPushTask error start -------')
            writeLog(mw.getTracebackInfo())
            writeLog('-----runBotPushTask error end -------')


def botPush():
    while True:
        runBotPushTask()
        time.sleep(1)


def runBotPushOtherTask():
    plist = getStartExtCfgByTag('other')
    for p in plist:
        try:
            script = p['name'].split('.')[0]
            __import__(script).run(bot)
        except Exception as e:
            writeLog('-----runBotPushOtherTask error start -------')
            writeLog(mw.getTracebackInfo())
            writeLog('-----runBotPushOtherTask error end -------')


def botPushOther():
    while True:
        runBotPushOtherTask()
        time.sleep(1)


def runBot(bot):
    try:
        bot.polling()
    except Exception as e:
        writeLog('-----runBot error start -------')
        writeLog(str(e))
        writeLog('-----runBot error end -------')
        time.sleep(1)
        runBot(bot)

if __name__ == "__main__":

    # 机器人推送任务
    botPushTask = threading.Thread(target=botPush)
    botPushTask.start()

    # 机器人其他推送任务
    botPushOtherTask = threading.Thread(target=botPushOther)
    botPushOtherTask.start()

    writeLog('启动成功')
    runBot(bot)


# asyncio.run(bot.polling())