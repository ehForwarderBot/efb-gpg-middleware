# coding=utf-8

import logging
import os
import pickle
import uuid
from gettext import translation
from typing import Optional, Dict, Tuple

import gnupg
import yaml
from pkg_resources import resource_filename

from ehforwarderbot import Middleware, Message, utils, MsgType, coordinator
from ehforwarderbot.chat import SelfChatMember
from ehforwarderbot.exceptions import EFBException
from ehforwarderbot.types import ChatID, MessageID
from .__version__ import __version__ as version


class GPGMiddleware(Middleware):
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

    key: str = ""
    password: str = ""
    always_trust: bool = True
    binary: str = "gpg"
    server: str = "pgp.mit.edu"
    encrypt_all: bool = False

    gpg: gnupg.GPG = None

    translator = translation("efb_gpg_middleware",
                             resource_filename("efb_gpg_middleware", "locale"),
                             fallback=True)
    _ = translator.gettext

    def __init__(self, instance_id: str = None):
        super().__init__(instance_id)

        storage_path = utils.get_data_path(self.middleware_id)
        config_path = utils.get_config_path(self.middleware_id)
        if not os.path.exists(config_path):
            raise EFBException(self._("GnuPG middleware is not configured."))
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

        self.logger = logging.getLogger("blueset.gpg")

    def process_message(self, message: Message) -> Optional[Message]:
        self.logger.debug("Received message: %s", message)
        if not message.type == MsgType.Text:
            return message
        self.logger.debug("[%s] is a text message.", message.uid)
        chat_key = (message.chat.module_id, message.chat.id)
        is_self = isinstance(message.author, SelfChatMember)
        if message.text and message.text.startswith("gpg`show") and is_self:
            self.logger.debug("[%s] is a text message.", message.uid)
            if chat_key in self.mappings:
                text = self._("This chat has GPG key: {0}").format(self.mappings[chat_key])
            else:
                text = self._("This chat has no GPG key.")
            self.reply_message(message, text)
            return
        elif message.text and message.text.startswith("gpg`clear") and is_self:
            if chat_key in self.mappings:
                del self.mappings[chat_key]
                pickle.dump(self.mappings, open(self.mappings_path, 'wb'))
            self.reply_message(message, self._("This chat now has no GPG key."))
            return
        elif message.text and message.text.strip().startswith("gpg`search"):
            if message.text.strip().startswith("gpg`search ") and \
                    len(message.text.strip()) > len("gpg`search ") and is_self:
                _, query = message.text.split(' ', 1)
                result = self.gpg.search_keys(query, self.server)
                if result:
                    text = self._("Found the following keys: ")
                    for i in result:
                        text += "\n {} {}".format(i['keyid'], ", ".join(i['uids']))
                else:
                    text = "No key is found with {}.".format(query)
            else:
                text = self._("Usage: gpg`search query")
            self.reply_message(message, text)
            return
        elif message.text and message.text.strip().startswith("gpg`bind"):
            if message.text.strip().startswith("gpg`bind ") and \
                    len(message.text.strip()) > len("gpg`bind ") and is_self:
                _, key = message.text.split(' ', 1)
                if all(i in '0123456789abcdefABCDEF' for i in key):
                    known_keys = self.gpg.list_keys()
                    if all(not i['fingerprint'].lower().endswith(key.lower()) for i in known_keys):
                        result = self.gpg.recv_keys(self.server, key)
                        if not result or not result[0].get('ok', 0):
                            text = self._("Key {0} not found.").format(key)
                        else:
                            self.mappings[chat_key] = key
                            pickle.dump(self.mappings, open(self.mappings_path, 'wb'))
                            text = self._("Key {0} is now for this chat.").format(key)
                    else:
                        self.mappings[chat_key] = key
                        pickle.dump(self.mappings, open(self.mappings_path, 'wb'))
                        text = self._("Key {0} is now for this chat.").format(key)
                else:
                    text = self._("{0} is not a valid key.").format(key)
            else:
                text = self._("Usage: gpg`bind FingerPrintHex")
            self.reply_message(message, text)
            return
        else:
            if is_self and chat_key in self.mappings:
                crypt = str(self.gpg.encrypt(message.text, self.mappings[chat_key],
                                             always_trust=self.always_trust))
                if crypt:
                    message.text = crypt
            elif not is_self:
                try:
                    plain = str(self.gpg.decrypt(message.text, always_trust=self.always_trust,
                                                 passphrase=self.password))
                    if plain:
                        message.text = plain
                except:
                    pass
            return message

    def reply_message(self, message: Message, text: str):
        author = message.chat.make_system_member(name=self.middleware_name, id=ChatID("__blueset.middleware__"), middleware=self)
        coordinator.send_message(Message(
            text=text,
            chat=message.chat,
            author=author,
            type=MsgType.Text,
            deliver_to=coordinator.master,
            target=message,
            uid=MessageID(str(uuid.uuid4())),
        ))
