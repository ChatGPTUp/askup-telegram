#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import logging
import os
import sys

import hupper

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from gpt_util import chatgpt_callback_response
from messages_db import get_messages, put_message, clear_messages

TOKEN = os.environ['TOKEN']

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def newchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /newchat is issued."""
    clear_messages(user_id=update.message.from_user.id)
    logger.info(f"New chat for user {update.message.from_user.id}")
    await update.message.reply_text("Let's do New Chat!")


async def askup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ AskUp Main """

    msg = await update.message.reply_text('...')

    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name

    new_message = {'role': 'user',
                   'content': f"{first_name}: {update.message.text}"}
    messages = get_messages(user_id=user_id) + [new_message]
    logger.debug(f"Messages: {messages} for user {user_id}")

    response = await chatgpt_callback_response(messages=messages,
                                               call_back_func=context.bot.edit_message_text,
                                               call_back_args={"chat_id": update.message.chat_id,
                                                               "message_id": msg.message_id})

    await context.bot.edit_message_text(chat_id=update.message.chat_id,
                                        message_id=msg.message_id,
                                        text=response)

    # Update DB
    put_message(user_id=user_id, message=new_message)
    put_message(user_id=user_id, message={
                'role': 'assistant', 'content': response})


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newchat", newchat_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, askup))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


def start_reloader():
    reloader = hupper.start_reloader('askup.main', verbose=True)
    sys.exit(reloader.wait_for_exit())


if __name__ == "__main__":
    if 'reload' in sys.argv:
        start_reloader()
    else:
        main()
