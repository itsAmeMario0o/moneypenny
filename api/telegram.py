"""Telegram bot: sends alerts to your phone and listens for commands.

Uses the plain Telegram Bot HTTP API (https://core.telegram.org/bots/api), so
no extra library is needed. Listening uses "long polling": we ask Telegram for
new messages and it holds the request open until one arrives. That means no
public web address is required.

Everything is switched off unless TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def is_enabled():
    return BOT_TOKEN != "" and CHAT_ID != ""


def call_telegram(method, params, timeout=40):
    """Call one Bot API method and return the decoded JSON reply."""
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/" + method
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(url, data=data, timeout=timeout) as reply:
        return json.loads(reply.read())


def send_message(text):
    """Send an alert to your chat. Does nothing if Telegram is off; never raises."""
    if not is_enabled():
        return
    try:
        call_telegram("sendMessage", {"chat_id": CHAT_ID, "text": text})
    except Exception as error:
        print("telegram send failed:", error)


def parse_command(text):
    """Split '/thesis nvda' into ('/thesis', 'NVDA'). The argument may be empty."""
    words = text.strip().split()
    if len(words) == 0:
        return "", ""
    command = words[0].lower().split("@")[0]  # '/thesis@MyBot' -> '/thesis'
    argument = ""
    if len(words) > 1:
        argument = words[1].upper()
    return command, argument


def listen_forever(handle_command):
    """Loop forever, passing each command from *your* chat to handle_command(command, argument).

    handle_command returns the text to reply with.
    """
    next_update_id = 0
    while True:
        try:
            reply = call_telegram("getUpdates", {"offset": next_update_id, "timeout": 30})
            for update in reply["result"]:
                next_update_id = update["update_id"] + 1
                message = update.get("message") or {}
                sender_chat = str(message.get("chat", {}).get("id", ""))
                if sender_chat != CHAT_ID:
                    continue  # ignore strangers who find the bot
                command, argument = parse_command(message.get("text", ""))
                send_message(handle_command(command, argument))
        except Exception as error:
            print("telegram listen failed:", error)
            time.sleep(10)


def start_listening(handle_command):
    if not is_enabled():
        return
    thread = threading.Thread(target=listen_forever, args=(handle_command,), daemon=True)
    thread.start()


if __name__ == "__main__":
    assert parse_command("/thesis nvda") == ("/thesis", "NVDA")
    assert parse_command("/Thesis@MoneypennyBot csco extra") == ("/thesis", "CSCO")
    assert parse_command("/help") == ("/help", "")
    assert parse_command("   ") == ("", "")
    print("telegram ok")
