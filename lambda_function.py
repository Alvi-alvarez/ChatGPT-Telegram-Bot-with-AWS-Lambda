import json
import boto3
import requests
import openai
import os


S3_CLIENT = boto3.client("s3")

# constants
OPENAI = os.environ["OPENIA_KEY"]
USER_ID = os.environ["USER_ID"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
S3_BUCKETS = os.environ["BUCKET_TOKEN"]
# if you want you can make the bot persinality not hardcoded by using environment variables
PERSINALITY = os.environ["PERSINALITY"]


# Define the Lambda handler function
def lambda_handler(event, context):
    # Convert the `event` object (containing incoming message content in JSON format) to a Python dictionary
    telegram_msg = json.dumps(event)
    telegram_msg = json.loads(telegram_msg)
    # Check if the incoming message is authorized to access the chat by comparing USER_ID
    if USER_ID != str(telegram_msg["message"]["from"]["id"]):
        return {"statusCode": 403, "body": str(telegram_msg["message"]["from"]["id"])}
    if str(telegram_msg["message"]["text"]) == "/clear":
        return clear_chat()
    else:
        return gpt(str(telegram_msg["message"]["text"]))


def clear_chat():
    try:
        save_file([{"role": "system", "content": PERSINALITY}])
        return send_msg(TELEGRAM_TOKEN, USER_ID, "🗑️")
    except Exception as e:
        return {"statusCode": 400, "message": str(e)}


def save_file(messages):
    try:
        file_name = "memory.json"
        upload_byte_stream = json.dumps(messages).encode("UTF-8")
        S3_CLIENT.put_object(Bucket=S3_BUCKETS, Key=file_name, Body=upload_byte_stream)
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}


def load_s3_object():
    try:
        file_name = "memory.json"
        obj = S3_CLIENT.get_object(Bucket=S3_BUCKETS, Key=file_name)
        file_content = obj["Body"].read().decode("utf-8")
        return json.loads(file_content)
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}


def gpt(input):
    openai.api_key = OPENAI
    send_typing(USER_ID, TELEGRAM_TOKEN)
    msgs = load_s3_object()
    msgs.append({"role": "user", "content": input})
    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=msgs)
    msgs.append({"role": "assistant", "content": str(chat.choices[0].message.content)})
    save_file(msgs)
    return send_msg(TELEGRAM_TOKEN, USER_ID, str(chat.choices[0].message.content))


# This is not necessary but it looks cool
def send_typing(USER_ID, TELEGRAM_TOKEN):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    params = {"chat_id": USER_ID, "action": "TYPING"}
    requests.post(f"{api_url}sendChatAction", data=params).json()


def send_msg(TELEGRAM_TOKEN, USER_ID, telegram_msg):
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    params = {"chat_id": USER_ID, "text": telegram_msg, "parse_mode": "MARKDOWN"}
    res = requests.post(f"{api_url}sendMessage", data=params).json()
    if res["ok"]:
        return {
            "statusCode": 200,
            "body": res["result"],
        }
    return {"statusCode": 400, "body": res}
