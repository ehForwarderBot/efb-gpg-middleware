import os
import pickle
import logging
import uuid
from typing import Optional, Dict, Tuple

from ehforwarderbot import EFBMiddleware, EFBMsg, utils, MsgType, EFBChat, ChatType, coordinator
from ehforwarderbot.exceptions import EFBException
import gnupg
import yaml

from .__version__ import __version__ as version


class GPGMiddleware(EFBMiddleware):
    """
    Configuration:

    .. code-block: yaml

        key: BD6B65EC00638DC9083781D5D4B65BB1A106200A
        password: test
        always_trust: true
        binary: /usr/bin/gpg
        server: pgp.mit.edu
    """
    middleware_id: str = "blueset.gpg"
    middleware_name: str = "GnuPG Middleware"
    __version__: str = version

    mappings: Dict[Tuple[str, str], str] = {}
    chat: EFBChat = None

    key: str = None
    password: str = None
    always_trust: bool = True
    binary: str = "gpg"
    server: str = "pgp.mit.edu"
    encrypt_all: bool = False

    gpg: gnupg.GPG = None

    def __init__(self):
        storage_path = utils.get_data_path(self.middleware_id)
        config_path = utils.get_config_path(self.middleware_id)
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
        if not os.path.exists(config_path):
            raise EFBException("GnuPG middleware is not configured.")
        else:
            config = yaml.load(open(config_path))
            self.key = config['key']
            self.always_trust = config.get('always_trust', self.always_trust)
            self.binary = config.get('binary', self.binary)
            self.password = config.get('password', self.password)
            self.server = config.get('server', self.server)

        self.gpg = gnupg.GPG(gpgbinary=self.binary)

        self.mappings_path = os.path.join(storage_path, "keymap.pkl")
        if os.path.exists(self.mappings_path):
            self.mappings = pickle.load(open(self.mappings_path, 'rb'))

        self.chat = EFBChat()
        self.chat.channel_name = self.middleware_name
        self.chat.channel_id = self.middleware_id
        self.chat.channel_emoji = "🔐"
        self.chat.chat_uid = "__blueset.gpg__"
        self.chat.chat_name = self.middleware_name
        self.chat.chat_type = ChatType.System

        self.logger = logging.getLogger("blueset.gpg")

    def process_message(self, message: EFBMsg) -> Optional[EFBMsg]:
        self.logger.debug("Received message: %s", message)
        if not message.type == MsgType.Text:
            return message
        self.logger.debug("[%s] is a text message.", message.uid)
        chat_key = (message.chat.channel_id, message.chat.chat_uid)
        is_self = message.author.is_self
        if message.text.startswith("gpg`show") and is_self:
            self.logger.debug("[%s] is a text message.", message.uid)
            if chat_key in self.mappings:
                text = "This chat has GPG key: {}".format(self.mappings[chat_key])
            else:
                text = "This chat has no GPG key."
            self.reply_message(message, text)
            return
        elif message.text.startswith("gpg`clear") and is_self:
            if chat_key in self.mappings:
                del self.mappings[chat_key]
                pickle.dump(self.mappings, open(self.mappings_path, 'wb'))
            self.reply_message(message, "This chat now has no GPG key.")
            return
        elif message.text.strip().startswith("gpg`search"):
            if message.text.strip().startswith("gpg`search ") and \
                    len(message.text.strip()) > len("gpg`search ") and is_self:
                _, query = message.text.split(' ', 1)
                result = self.gpg.search_keys(query, self.server)
                if result:
                    text = "Found the following keys: "
                    for i in result:
                        text += "\n {} {}".format(i['keyid'], ", ".join(i['uids']))
                else:
                    text = "No key is found with {}.".format(query)
            else:
                text = "Usage: gpg`search query"
            self.reply_message(message, text)
            return
        elif message.text.strip().startswith("gpg`bind"):
            if message.text.strip().startswith("gpg`bind ") and \
                    len(message.text.strip()) > len("gpg`bind ") and is_self:
                _, key = message.text.split(' ', 1)
                if all(i in '0123456789abcdefABCDEF' for i in key):
                    known_keys = self.gpg.list_keys()
                    if all(not i['fingerprint'].lower().endswith(key.lower()) for i in known_keys):
                        result = self.gpg.recv_keys(self.server, key)
                        if not result or not result[0].get('ok', 0):
                            text = "Key {} not found.".format(key)
                        else:
                            self.mappings[chat_key] = key
                            pickle.dump(self.mappings, open(self.mappings_path, 'wb'))
                            text = "Key {} is now for this chat.".format(key)
                    else:
                        self.mappings[chat_key] = key
                        pickle.dump(self.mappings, open(self.mappings_path, 'wb'))
                        text = "Key {} is now for this chat.".format(key)
                else:
                    text = "{} is not a valid key.".format(key)
            else:
                text = "Usage: pgp`bind FingerPrintHex"
            self.reply_message(message, text)
            return
        else:
            if message.author.is_self and chat_key in self.mappings:
                crypt = str(self.gpg.encrypt(message.text, self.mappings[chat_key],
                                             always_trust=self.always_trust))
                if crypt:
                    message.text = crypt
            elif not message.author.is_self:
                plain = str(self.gpg.decrypt(message.text, always_trust=self.always_trust,
                                             passphrase=self.password))
                if plain:
                    message.text = plain
            return message

    def reply_message(self, message: EFBMsg, text: str):
        reply = EFBMsg()
        reply.text = text
        reply.chat = coordinator.slaves[message.chat.channel_id].get_chat(message.chat.chat_uid)
        reply.author = self.chat
        reply.type = MsgType.Text
        reply.deliver_to = coordinator.master
        reply.target = message
        reply.uid = str(uuid.uuid4())
        coordinator.send_message(reply)
