import os

import openai

CHATGPT_ENGINE = os.getenv("CHATGPT_ENGINE", "gpt-3.5-turbo")
BOT_PENCIL_ICON = os.getenv("BOT_PENCIL_ICON", "*")

UPDATE_CHAR_RATE = 3

openai.api_key = os.environ["OPENAI_API_KEY"]


async def chatgpt_callback_response(messages, call_back_func, call_back_args):
    try:
        response = openai.ChatCompletion.create(
            model=CHATGPT_ENGINE,
            messages=messages,
            stream=True,
        )

        content = ""

        # Stream each message in the response to the user in the same thread
        counter = 0
        for completions in response:
            counter += 1
            if "content" in completions.choices[0].delta:
                content += completions.choices[0].delta.get("content")

            if call_back_func and call_back_args:
                if counter % UPDATE_CHAR_RATE == 1:
                    # Send or update the message,
                    # depending on whether it's the first or subsequent messages
                    call_back_args['text'] = content+BOT_PENCIL_ICON
                    await call_back_func(**call_back_args)

        return content

    except (KeyError, IndexError) as e:
        return "GPT3 Error: " + str(e)
    except Exception as e:
        return "GPT3 Unknown Error: " + str(e)
