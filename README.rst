EFB GPG Middleware
==================

.. image:: https://img.shields.io/pypi/v/efb-gpg-middleware.svg
   :alt: PyPI release
   :target: https://pypi.org/project/efb-gpg-middleware/
.. image:: https://pepy.tech/badge/efb-gpg-middleware/month
   :alt: Downloads per month
   :target: https://pepy.tech/project/efb-gpg-middleware
.. image:: https://d322cqt584bo4o.cloudfront.net/ehforwarderbot/localized.svg
   :alt: Translate this project
   :target: https://crowdin.com/project/ehforwarderbot/

.. image:: https://github.com/blueset/efb-gpg-middleware/raw/master/banner.png
   :alt: Banner

**Module ID**: ``blueset.gpg``

A middleware for EH Forwarder Bot that encrypts and
decrypts messages using GnuPG.

This middleware simply encrypts outgoing messages with
recipients' registered public key, and decrypt incoming
messages with your own secret key.

All encrypted messages should be and will be ASCII
armored. All messages that was not successfully
encrypted/decrypted will be delivered untouched.

This middleware only encrypt/decrypt text messages.
Other types of messages are kept untouched.

Dependencies
------------

* EH Forwarder Bot >=2.0
* GnuPG
* An imported key pair that is used to decrypt incoming
  messages

Getting Started
---------------

1. Make sure you have access to a public key server
   of your choice using the ``gpg`` installed.
2. Have at least one key pair registered in local GPG.
3. Install this middleware::

    pip3 install efb-gpg-middleware

4. Create a config file in your current EFB profile:
   ``<PATH_TO_EFB_PROFILE>/blueset.gpg/config.yaml``::

        # Signature of your own key pair (required)
        key: BD6B65EC00638DC9083781D5D4B65BB1A106200A

        # Passphrase to the key pair (optional)
        password: test

        # Trust all key in the local stoage
        # (optional, default: true)
        always_trust: true

        # Path to the GPG binary
        # (optional, default: search from $PATH)
        binary: /usr/bin/gpg

        # Preferred public key server
        # (optional, default: pgp.mit.edu)
        server: pgp.mit.edu


How to use
----------

Send commands as text messages in chats to interact with
the middleware. All command messages will not be
delivered to slave channel.

* ``gpg`info``: Show the key fingerprint used for this chat.
* ``gpg`search query``: Search for a key from the key server.
* ``gpg`bind fingerprinthex``: Use key for specified fingerprint for a chat.
* ``gpg`clear``: Do not encrypt messages sent to this chat.

When you have told the middleware to use a key for a chat,
it will encrypt all your text messages sent to this chat with
the key specified.

The middleware will try to decrypt all incoming text messages
with GnuPG regardless of settings, and only update the message
if the decryption is successful.

Footnote
--------

If you find this module not as useful, don’t be disappointed. This is just
a demo to show you what you can do with EFB Middlewares.

Experimental localization support
---------------------------------

GPG Middleware supports localized user interface prompts
experimentally, by setting the locale environmental variable
(``LANGUAGE``, ``LC_ALL``, ``LC_MESSAGES`` or ``LANG``) to one
of our `supported languages`_. Meanwhile, you can help to
translate this project into your languages on `our Crowdin page`_.

.. _supported languages: https://crowdin.com/project/ehforwarderbot/
.. _our Crowdin page: https://crowdin.com/project/ehforwarderbot/