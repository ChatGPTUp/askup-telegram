import ast
import asyncio
import logging
import os
import json

import requests
import yaml
from gpt_util import chatgpt_callback_response
from prompts import PLUGIN_SELECT_PROMPT, PLUGIN_RESULT_PROMPT

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

PLUGIN_HOST = os.environ["PLUGIN_HOST"]


def fetch_and_parse_json(url=PLUGIN_HOST):
    response = requests.get(f"{url}/.well-known/ai-plugin.json")
    data = response.json()

    name_for_human = data["name_for_human"]
    description_for_model = data["description_for_model"]
    open_api_yml_url = data["api"]["url"]

    api_host, api_prompt = fetch_and_parse_yaml(open_api_yml_url)

    logger.info(f"api_host: {api_host}")

    return (
        name_for_human,
        api_host,
        f"{PLUGIN_SELECT_PROMPT}\n{description_for_model}\n{api_prompt}",
    )


def fetch_and_parse_yaml(full_url):
    prompt = ""
    response = requests.get(full_url)
    data = yaml.safe_load(response.text)

    api_host = data["servers"][0]["url"]

    paths = data.get("paths", {})
    for path, path_data in paths.items():
        for method, method_data in path_data.items():
            summary = method_data.get("summary", "")
            parameters = method_data.get("parameters", [])
            param_str = ""
            for parameter in parameters:
                param_str += f"{parameter.get('name', '')} "

            prompt += (
                f"For {summary}, please call path `{path}` with specify `{param_str}`\n"
            )

    return api_host, prompt


def get_api_json_result(api_host, api_call_info):
    # Parse the string into a dictionary
    d = ast.literal_eval(api_call_info)

    # Extract the path and query
    path = d.get("path", "")
    query = d.get("query", "")

    response = requests.get(f"{api_host}{path}?query={query}", timeout=10)
    return response.json()


async def ask_plugin_stage1(
    query, prompt, call_back_func=None, call_back_args=None, memory=[]
):
    messages = (
        [{"role": "system", "content": prompt}]
        + memory
        + [{"role": "user", "content": query}]
    )

    gpt_response = await chatgpt_callback_response(
        messages=messages, call_back_func=call_back_func, call_back_args=call_back_args
    )
    logger.info("Plugin response: %s", gpt_response)
    return gpt_response


async def ask_plugin_stage2(
    query, api_json_result, call_back_func=None, call_back_args=None, memory=[]
):
    messages = (
        [{"role": "system", "content": PLUGIN_RESULT_PROMPT}]
        + memory
        + [
            {
                "role": "assistant",
                "content": json.dumps(api_json_result, indent=1)[:1000],
            },
            {"role": "user", "content": query},
        ]
    )

    final_response = await chatgpt_callback_response(
        messages=messages, call_back_func=call_back_func, call_back_args=call_back_args
    )
    logger.info("Final response: %s", final_response)
    return final_response


async def ask_plugin(q):
    name, api_host, prompt = fetch_and_parse_json(PLUGIN_HOST)

    api_host, api_call_info = await ask_plugin_stage1(q, prompt)
    api_json_result = get_api_json_result(api_host, api_call_info)

    final_response = await ask_plugin_stage2(q, api_json_result, None, None)
    return final_response


if __name__ == "__main__":
    result = asyncio.run(ask_plugin(q="요즈음 딥러닝 소식 알려줘"))
    print(result)
    result = asyncio.run(ask_plugin(q="주말에 볼만한 재미있는 SF 영화 추천해줘"))
    print(result)
