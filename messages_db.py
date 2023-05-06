from tinydb import TinyDB, Query

# Configure the path to the database file
local_db_path = "local_messages_db.json"
db = TinyDB(local_db_path)
User = Query()

SYSTEM_INSTRUCT = """You are AskUp, AI ChatBot in Telegram. 
Please provide concise and wise answers to the questions asked by the users.
Try to be fun and engaging, but also polite and respectful.
"""


def put_message(user_id, message, max_length=1500):
    user = db.get(User.user_id == user_id)

    if user:
        user["messages"].append(message)

        # Check if the total content length exceeds max_length and remove old messages if necessary
        total_content_length = sum(len(msg["content"])
                                   for msg in user["messages"])
        while total_content_length > max_length:
            removed_message = user["messages"].pop(0)
            total_content_length -= len(removed_message["content"])

        db.update(user, User.user_id == user_id)
    else:
        db.insert({"user_id": user_id, "messages": [message]})


def get_messages(user_id, max_length=1500):
    user = db.get(User.user_id == user_id)

    if not user:
        return [{"role": "system", "content": SYSTEM_INSTRUCT}]

    # Get messages within max_length constraint
    messages = []
    total_content_length = 0

    for msg in reversed(user["messages"]):
        if total_content_length + len(msg["content"]) <= max_length:
            messages.insert(0, msg)
            total_content_length += len(msg["content"])
        else:
            break

    # Insert system
    messages.insert(0, {"role": "system", "content": SYSTEM_INSTRUCT})
    return messages

def clear_messages(user_id):
    user = db.get(User.user_id == user_id)

    if user:
        user["messages"] = []
        db.update(user, User.user_id == user_id)
