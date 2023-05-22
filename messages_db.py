from tinydb import TinyDB, Query

# Configure the path to the database file
local_db_path = "local_messages_db.json"
db = TinyDB(local_db_path)
User = Query()


def put_message_list(user_id, message_list, max_length=1500):
    user = db.get(User.user_id == user_id)

    if user:
        user["messages"] = user["messages"] + message_list

        # Check if the total content length exceeds max_length and remove old messages if necessary
        total_content_length = sum(len(msg["content"]) for msg in user["messages"])
        while total_content_length > max_length:
            removed_message = user["messages"].pop(0)
            total_content_length -= len(removed_message["content"])

        db.update(user, User.user_id == user_id)
    else:
        db.insert({"user_id": user_id, "messages": message_list})


def get_messages(user_id, max_length=1500):
    user = db.get(User.user_id == user_id)
    if not user:
        return []

    # Get messages within max_length constraint
    messages = []
    total_content_length = 0

    for msg in reversed(user["messages"]):
        if total_content_length + len(msg["content"]) <= max_length:
            messages.insert(0, msg)
            total_content_length += len(msg["content"])
        else:
            break

    return messages


def clear_messages(user_id):
    user = db.get(User.user_id == user_id)

    if user:
        user["messages"] = []
        db.update(user, User.user_id == user_id)
