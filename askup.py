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
import json
import logging
import os
import sys

import hupper
from gpt_util import chatgpt_callback_response, chatgpt_response
from messages_db import clear_messages, get_messages, put_message_list
from plugin import (
    ask_plugin_stage1,
    ask_plugin_stage2,
    fetch_and_parse_json,
    get_api_json_result,
)
from prompts import MAIN_PROMPT
from telegram import Bot, ForceReply, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]

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


async def askup_02_plugin_memory(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """AskUp Main"""

    msg = await update.message.reply_text("...")

    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name
    query = update.message.text

    new_message = {"role": "user", "content": f"{first_name}: {update.message.text}"}
    memory = get_messages(user_id=user_id)

    logger.info("Memory: %s", json.dumps(memory, indent=2))

    name, api_host, prompt = fetch_and_parse_json()
    logger.info("Plugin: %s %s %s", name, api_host, prompt)
    api_call_info = await ask_plugin_stage1(
        query=query,
        prompt=prompt,
        call_back_func=context.bot.edit_message_text,
        call_back_args={
            "chat_id": update.message.chat_id,
            "message_id": msg.message_id,
        },
        memory=memory,
    )
    await context.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=msg.message_id,
        text=api_call_info,
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        api_json_result = get_api_json_result(api_host, api_call_info)
    except Exception as exception_info:
        # Update Partial DB
        put_message_list(
            user_id,
            message_list=[new_message, {"role": "assistant", "content": api_call_info}],
        )
        logger.error(exception_info)
        return

    msg = await update.message.reply_text(str(api_json_result)[:500])

    # Second message
    msg = await update.message.reply_text("...")

    final_response = await ask_plugin_stage2(
        query=query,
        api_json_result=api_json_result,
        call_back_func=context.bot.edit_message_text,
        call_back_args={
            "chat_id": update.message.chat_id,
            "message_id": msg.message_id,
        },
        memory=memory,
    )

    await context.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=msg.message_id,
        text=final_response,
        parse_mode=ParseMode.MARKDOWN,
    )

    # Update DB
    put_message_list(
        user_id=user_id,
        message_list=[
            new_message,
            {"role": "assistant", "content": api_call_info},
            {"role": "assistant", "content": final_response},
        ],
    )


async def askup_01_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """AskUp Main"""

    msg = await update.message.reply_text("...")

    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name
    query = update.message.text

    name, api_host, prompt = fetch_and_parse_json()
    api_call_info = await ask_plugin_stage1(
        query=query,
        prompt=prompt,
        call_back_func=context.bot.edit_message_text,
        call_back_args={
            "chat_id": update.message.chat_id,
            "message_id": msg.message_id,
        },
    )
    await context.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=msg.message_id,
        text=api_call_info,
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        api_json_result = get_api_json_result(api_host, api_call_info)
    except Exception as exception_info:
        logger.error(exception_info)
        return

    msg = await update.message.reply_text(str(api_json_result)[:500])

    # Second message
    msg = await update.message.reply_text("...")

    final_response = await ask_plugin_stage2(
        query=query,
        api_json_result=api_json_result,
        call_back_func=context.bot.edit_message_text,
        call_back_args={
            "chat_id": update.message.chat_id,
            "message_id": msg.message_id,
        },
    )

    await context.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=msg.message_id,
        text=final_response,
        parse_mode=ParseMode.MARKDOWN,
    )


async def askup_04_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """AskUp Main"""

    msg = await update.message.reply_text("...")

    user = update.message.from_user
    user_id = user.id
    first_name = user.first_name

    system_message = {"role": "system", "content": MAIN_PROMPT}
    new_message = {"role": "user", "content": f"{first_name}: {update.message.text}"}
    messages = [system_message] + get_messages(user_id=user_id) + [new_message]

    # Show messages in logs using lazy % formatting
    logger.info("Messages: %s", json.dumps(messages, indent=2))

    response = await chatgpt_callback_response(
        messages=messages,
        call_back_func=context.bot.edit_message_text,
        call_back_args={
            "chat_id": update.message.chat_id,
            "message_id": msg.message_id,
        },
    )

    await context.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=msg.message_id,
        text=response,
        parse_mode=ParseMode.MARKDOWN,
    )

    # Update DB
    put_message_list(
        user_id=user_id,
        message_list=[new_message, {"role": "assistant", "content": response}],
    )


async def askup_03_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    AskUp with streaming
    """
    msg = await update.message.reply_text("...")

    messages = [
        {"role": "system", "content": MAIN_PROMPT},
        {"role": "user", "content": update.message.text},
    ]

    response = await chatgpt_callback_response(
        messages=messages,
        call_back_func=context.bot.edit_message_text,
        call_back_args={
            "chat_id": update.message.chat_id,
            "message_id": msg.message_id,
        },
    )

    await context.bot.edit_message_text(
        chat_id=update.message.chat_id,
        message_id=msg.message_id,
        text=response,
        parse_mode=ParseMode.MARKDOWN,
    )


async def askup_02_simple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    AskUp simple QA
    """
    messages = [
        {"role": "system", "content": MAIN_PROMPT},
        {"role": "user", "content": update.message.text},
    ]

    gpt_response = chatgpt_response(messages=messages)
    await update.message.reply_text(gpt_response)


async def askup_01_echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    AskUp echo
    """
    await update.message.reply_text(update.message.text)


def main_hanlder(event=None, context=None) -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newchat", newchat_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, askup_04_memory)
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


def start_reloader():
    """Start the reloader"""
    reloader = hupper.start_reloader("askup.main_hanlder", verbose=True)
    sys.exit(reloader.wait_for_exit())


if __name__ == "__main__":
    if "reload" in sys.argv:
        start_reloader()
    else:
        # Run the async main function
        main_hanlder()
