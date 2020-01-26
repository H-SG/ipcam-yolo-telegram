#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import glob
import random
import conf_handler
import time

import re
import inflect
p = inflect.engine()

from functools import wraps
from telegram import ChatAction, ReplyKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Load config - this can probably also live in main
configPath = 'bot_conf.yaml'
conf_handler.loadConfig(configPath)

# keyboards
yncKeyboard = [['Yes'], ['No'], ['Cancel']]
yncMarkup = ReplyKeyboardMarkup(yncKeyboard, one_time_keyboard=True)
ynKeyboard = [['Yes'], ['No']]
ynMarkup = ReplyKeyboardMarkup(ynKeyboard, one_time_keyboard=True)

# whitelist command conversations
wlUSERNAMEENTERED, wlIDCONFIRM, wlDELETEENTERED, wlUSERNAMECONFIRM, wlIDENTERED, wlUSERNAMEEXISTS, wlDELETECONFIRM = range(7)

# check if user sending commands or chat is in whitelist
def restrictUsers(func):
    @wraps(func)
    def decorator(update, context, *args, **kwargs):
        userID = update.effective_chat.id
        if userID not in conf_handler.config['whiteList'].keys():
            update.message.reply_text(random.choice(conf_handler.config['blackListResponses']))
            return
        return func(update, context, *args, **kwargs)
    return decorator

# make the bot seem more human
def send_action(action):
    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(update, context,  *args, **kwargs)
        return command_func
    
    return decorator

# wrapper for photo responses
@send_action(ChatAction.UPLOAD_PHOTO)
def photoResponse(update, context, imgPath):
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(imgPath, 'rb'))

#######################
# main chat functions #
#######################

# whitelist command and management functions, mostly stuff to run the conversations
@restrictUsers
def whitelist(update, context):
    addList = ['add', 'user']
    rmList = ['rm', 'remove', 'del', 'delete']
    argsNum = len(context.args)
    if argsNum == 0:
        return listWhiteList(update, context)
    elif argsNum == 1:
        arg = context.args[0]
        if arg in addList:
            return usernameEntry(update, context)
        elif arg in rmList:
            return usernameRemoveEntry(update, context)
        else:
            return invalidAction(update, context)
    elif argsNum == 2:
        arg = context.args[0]
        if arg in addList:
            return usernameCheck(update, context)
        elif arg in rmList:
            return usernameDeleteCheck(update, context)
        else:
            return invalidAction(update, context)
    else:
        return invalidArgsNum(update, context)    

@send_action(ChatAction.TYPING)
def listWhiteList(update, context):
    time.sleep(0.5)
    wL = "Whitelisted users are:\n"
    for key, value in conf_handler.config['whiteList'].items():
        wL += ("{} with ID {}\n".format(value, key))
    update.message.reply_text(wL)
    return cleanExit(update, context)

@send_action(ChatAction.TYPING)
def usernameEntry(update, context):
    time.sleep(0.5)
    update.message.reply_text("What is the username?")
    return wlUSERNAMEENTERED

@send_action(ChatAction.TYPING)
def usernameRemoveEntry(update, context):
    time.sleep(0.5)
    update.message.reply_text("What is the username you want to remove?")
    return wlDELETEENTERED

@send_action(ChatAction.TYPING)
def usernameDelete(update, context):
    time.sleep(0.5)
    update.message.reply_text("Removing {} from whitelist".format(context.user_data['username']))
    remKey = None
    for key, value in conf_handler.config['whiteList'].items():
        if value == context.user_data['username']:
            remKey = key

    conf_handler.config['whiteList'].pop(remKey)
    conf_handler.saveConfig(configPath)
    return cleanExit(update, context)

@send_action(ChatAction.TYPING)
def usernameAdd(update, context):
    time.sleep(0.5)
    username = context.user_data['username']
    userid = context.user_data['id']
    for key, value in conf_handler.config['whiteList'].items():
        if key == userid:
            update.message.reply_text("Chat ID {} already exists for user {}".format(key, value))
            return idEntry(update, context)
    else:
        update.message.reply_text("Adding {} to whitelist".format(username))
        conf_handler.config['whiteList'].update({userid:username})
        conf_handler.saveConfig(configPath)
        return cleanExit(update, context)    

@send_action(ChatAction.TYPING)
def usernameDeleteCheck(update, context):
    time.sleep(0.5)
    try:
        text = context.args[1]
        context.user_data['username'] = text
    except: 
        text = update.message.text

    context.user_data['username'] = text

    if text in conf_handler.config['whiteList'].values():
        update.message.reply_text("Are you sure you want to delete user {}?".format(text), reply_markup=ynMarkup)
        return wlDELETECONFIRM
    else:
        update.message.reply_text("Username {} is not in the whitelist".format(text))
        return cleanExit(update, context)

@send_action(ChatAction.TYPING)
def invalidAction(update, context):
    time.sleep(0.5)
    update.message.reply_text("Don't know that action!")
    return cleanExit(update, context)

@send_action(ChatAction.TYPING)
def invalidArgsNum(update, context):
    time.sleep(0.5)
    update.message.reply_text("Now I'm just a simple city bot, but I don't understand all that extra stuff you're trying to say")
    return cleanExit(update, context)

@send_action(ChatAction.TYPING)
def usernameCheck(update, context):
    time.sleep(0.5)
    try:
        text = context.args[1]
        context.user_data['username'] = text
    except: 
        text = update.message.text

    context.user_data['username'] = text

    if text not in conf_handler.config['whiteList'].values():
        update.message.reply_text("Is the username '{}' correct?".format(text), reply_markup=yncMarkup)
        return wlUSERNAMECONFIRM
    else:
        update.message.reply_text("Username '{}' is already on the whitelist! Do you want to add a different user?".format(text), reply_markup=ynMarkup)
        return wlUSERNAMEEXISTS

@send_action(ChatAction.TYPING)
def idEntry(update, context):
    time.sleep(0.5)    
    update.message.reply_text("What is the chat ID for username {}?".format(context.user_data['username']))
    return wlIDENTERED

@send_action(ChatAction.TYPING)
def idCheck(update, context):
    time.sleep(0.5)
    try:
        text = context.args[1]
    except: 
        text = update.message.text

    try:
        context.user_data['id'] = int(text)
    except ValueError:
        update.message.reply_text("That is not a valid Chat ID, try again.")
        return idEntry(update, context)    

    update.message.reply_text("Is the chat ID '{}' correct for username {}?".format(text, context.user_data['username']), reply_markup=yncMarkup)
    return wlIDCONFIRM

@send_action(ChatAction.TYPING)
def id(update, context):
    update.message.reply_text("Your chat ID is: {}".format(update.effective_chat.id))

# last command and supporting functions
@restrictUsers
def last(update, context):
    argsNum = len(context.args)
    objType = None
    camera = 'all'
    nImg = 1
    if argsNum != 0:
        for arg in context.args:
            try:
                tempArg = int(arg)
                nImg = tempArg
            except:
                if arg in conf_handler.config['cameraPaths'].keys():
                    camera = arg
                elif arg in conf_handler.config['objects']:
                    objType = arg
                else:
                    return invalidAction(update, context)
        else:
            lastImage(update, context, camera, nImg, objType)
    else:
        lastImage(update, context, camera, nImg, objType)

@send_action(ChatAction.TYPING)
def lastImage(update, context, camera='all', nImg=1, objType=None):
    imagePath = imageFinder(conf_handler.config['cameraPaths'][camera], objType, nImg)
    
    cameraSet = camera != 'all'
    objTypeSet = objType is not None

    if imagePath is None:
        update.message.reply_text("No image files were found matching the search parameters!")
    else:                  
        for i, path in enumerate(imagePath):
            if cameraSet:
                camString = "{} camera".format(camera)
            else:
                location = "/".join(path.split("/")[1:3])
                for key, value in conf_handler.config['cameraPaths'].items():
                    if value == location:
                        location = key
                        break
                camString = "{} camera".format(location)

            # create search object string
            if objTypeSet:
                objString = "a {}".format(objType)
            else:
                objString = "any object"
            
            # create detected object list string
            objList = []
            for obj in conf_handler.config['objects']:
                if obj in path:
                    objList.append(obj)
            objListString = " and a ".join(objList)

            # create image ordinal string
            if (nImg == 1) or (i == len(imagePath) - 1):
                imgOrdinalString = "last"
            else:
                imgOrdinalString = "{} last".format(p.number_to_words(p.ordinal(len(imagePath) - i)))
                
            # phrasing logic
            if objTypeSet and cameraSet:
                replyString = "The {} image with {} at the {} contained a {}".format(imgOrdinalString, objString, camString, objListString)
            elif cameraSet:
                replyString = "The {} {} image with {} contained a {}".format(imgOrdinalString, camString, objString, objListString)
            else:
                replyString = "The {} image with {} was at the {} and contained a {}".format(imgOrdinalString, objString, camString, objListString)

            update.message.reply_text(replyString)

            with open(path, 'rb') as f:
                update.message.reply_photo(f)

# find images in folder, return n newest images matching objType
def imageFinder(cameraPath, objType=None, nImg=1):
    if objType is None:
        list_of_files = glob.glob('./{}/*.jpg'.format(cameraPath, objType))
    else:
        list_of_files = glob.glob('./{}/*{}*.jpg'.format(cameraPath, objType))

    # this seems lazy
    latest_files = sorted(list_of_files, key=os.path.getctime)
    nFilesFound = len(latest_files)
    if nFilesFound == 0:
        latest_files = None
    elif nFilesFound < nImg:
        latest_files = latest_files[-nFilesFound:]
    else:
        latest_files = latest_files[-nImg:]

    return latest_files

def newImageFinder(cameraPath, time, objType='person'):
    list_of_files = glob.glob('./{}/*{}*.jpg'.format(cameraPath, objType))
    latest_files = sorted(list_of_files, key=os.path.getctime, reverse=True)
    newFiles = []
    for f in latest_files:
        if os.path.getctime(f) > time:
            newFiles.append(f)
        else:
            break

    return newFiles



@send_action(ChatAction.TYPING)
@restrictUsers
def status(update, context):
    """Send a message when the command /status is issued."""
    update.message.reply_text(text="Strandhuis bot is running!")

@send_action(ChatAction.TYPING)
@restrictUsers
def start(update, context):
    update.message.reply_text(text="Hello! I'm Strandhuisbot")

@send_action(ChatAction.TYPING)
@restrictUsers
def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Current commands are:\n - Get last image from a camera: /last <# images> <camera> <object>\n - Get current whitelist: /whitelist\n - Get chat ID: /id')

@send_action(ChatAction.TYPING)
def cancelCommand(update, context):
    update.message.reply_text('Command cancelled')
    return cleanExit(update, context)

@send_action(ChatAction.TYPING)
def useKeyboard(update, context):
    update.message.reply_text("I'd really prefer it if you used the custom keyboard I made specially for this")
    return cleanExit(update, context)

def cleanExit(update, context):
    context.user_data.clear()
    return ConversationHandler.END

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

@send_action(ChatAction.TYPING)
@restrictUsers
def emma(update, context):
    time.sleep(0.5)
    update.message.reply_text('All I know about Emma is that she is the best dog *IN THE WORLD*!', parse_mode=ParseMode.MARKDOWN)

@send_action(ChatAction.TYPING)
@restrictUsers
def judy(update, context):
    time.sleep(0.5)
    update.message.reply_text('All I know about Judy is that she is the best wife *IN THE WORLD*!', parse_mode=ParseMode.MARKDOWN)

@send_action(ChatAction.TYPING)
@restrictUsers
def echo(update, context):
    time.sleep(0.5)
    update.message.reply_text(random.choice(conf_handler.config['chatResponses']))

#@send_action(ChatAction.UPLOAD_PHOTO)
def newImages(context):
    newImagePaths = newImageFinder(conf_handler.config['cameraPaths']['all'], context.job.context.user_data['checkTime'])
    if len(newImagePaths) > 0:
        context.bot.send_message(context.job.context.user_data['id'], text="A person has been detected!")
        context.job.context.user_data['checkTime'] = time.time()
        for path in newImagePaths[:2]:
            with open(path, 'rb') as f:
                context.bot.send_photo(context.job.context.user_data['id'], photo=f)

@send_action(ChatAction.TYPING)
@restrictUsers
def monitor(update, context):
    argsNum = len(context.args)
    if argsNum != 0:
        for arg in context.args:
            if arg == 'start':
                if 'job' in context.chat_data:
                    update.message.reply_text("The camera monitor is already running")
                else:
                    context.user_data['checkTime'] = time.time()
                    context.user_data['id'] = update.effective_chat.id
                    newMonitor = context.job_queue.run_repeating(newImages, interval=30, first=0, context=context)
                    context.chat_data['job'] = newMonitor
                    update.message.reply_text("The camera monitor has been started")
            elif arg == 'stop':
                if 'job' in context.chat_data:
                    oldMonitor = context.chat_data['job']
                    oldMonitor.schedule_removal()
                    update.message.reply_text("The camera monitor has been stopped")
                    context.chat_data.clear()
                else:
                    update.message.reply_text("The camera monitor is not currently running")
            else:
                return invalidAction
    else:
        time.sleep(0.5)
        if 'job' in context.chat_data:            
            update.message.reply_text("The camera monitor is running")
        else:
            update.message.reply_text("The camera monitor is not running")

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(conf_handler.config['token'], use_context=True)

    #jq = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("last", last))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("id", id))
    dp.add_handler(CommandHandler("monitor", monitor, pass_args=True, pass_job_queue=True, pass_chat_data=True))


    # whitelist conversations
    whiteListConv = ConversationHandler(
        entry_points=[CommandHandler('whitelist', whitelist)],

        states={
            wlUSERNAMEENTERED: [MessageHandler(Filters.text, usernameCheck)],

            wlUSERNAMECONFIRM: [MessageHandler(Filters.regex('^(Yes)$'), idEntry),
                                MessageHandler(Filters.regex('^(No)$'), usernameEntry),
                                MessageHandler(Filters.regex('^(Cancel)$'), cancelCommand),
                                MessageHandler(Filters.text, useKeyboard)],

            wlUSERNAMEEXISTS: [MessageHandler(Filters.regex('^(Yes)$'), usernameEntry),
                               MessageHandler(Filters.regex('^(No)$'), cancelCommand),
                               MessageHandler(Filters.text, useKeyboard)],

            wlIDENTERED: [MessageHandler(Filters.text, idCheck)],

            wlIDCONFIRM: [MessageHandler(Filters.regex('^(Yes)$'), usernameAdd),
                          MessageHandler(Filters.regex('^(No)$'), idEntry),
                          MessageHandler(Filters.regex('^(Cancel)$'), cancelCommand),
                          MessageHandler(Filters.text, useKeyboard)],

            wlDELETECONFIRM: [MessageHandler(Filters.regex('^(Yes)$'), usernameDelete),
                               MessageHandler(Filters.regex('^(No)$'), cancelCommand),
                               MessageHandler(Filters.text, useKeyboard)],
                     
            wlDELETEENTERED: [MessageHandler(Filters.text, usernameDeleteCheck)]                        
                },

        fallbacks=[MessageHandler(Filters.regex(re.compile('^(no|n|cancel|c|done)$', re.IGNORECASE)), cancelCommand)]
    )

    dp.add_handler(whiteListConv)

    # on noncommand i.e messages
    dp.add_handler(MessageHandler(Filters.regex(re.compile('(Emma)', re.IGNORECASE)), emma))
    dp.add_handler(MessageHandler(Filters.regex(re.compile('(Judy)', re.IGNORECASE)), judy))

    # any other conversational flotsam
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
