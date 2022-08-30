"""Functions and classes related to sending Telegram messages"""
import json
import typing
from typing import Union

import requests

from flathunter.abstract_notifier import Notifier
from flathunter.abstract_processor import Processor
from flathunter.exceptions import BotBlockedException, UserDeactivatedException
from flathunter.logging import logger


class SenderTelegram(Processor, Notifier):
    """Expose processor that sends Telegram messages"""

    def __init__(self, config, receivers=None):
        self.config = config
        self.bot_token = self.config.telegram_bot_token()
        self.__images_enabled = str(self.config.get('telegram', {}).get('images_enabled', 'false')).lower() == 'true'

        self.__text_message_url = "https://api.telegram.org/bot%s/sendMessage" % self.bot_token
        self.__media_group_url = "https://api.telegram.org/bot%s/sendMediaGroup" % self.bot_token

        if receivers is None:
            self.receiver_ids = self.config.telegram_receiver_ids()
        else:
            self.receiver_ids = receivers

    def process_expose(self, expose):
        """Send a message to a user describing the expose"""
        self.__broadcast(
            receivers=self.receiver_ids,
            message=self.__get_text_message(expose),
            images=self.__get_images(expose),
        )
        return expose

    def __broadcast(self, receivers: typing.List[int], message: str, images: typing.List[str]):
        for receiver in receivers:
            msg = self.__send_text(receiver, message)
            if self.__images_enabled and msg != {} and len(images):
                self.__send_images(chat_id=receiver, msg=msg, images=images)

    def notify(self, message: str):
        """Send messages to each of the receivers in receiver_ids"""
        for receiver in self.receiver_ids:
            self.__send_text(chat_id=receiver, message=message)

    def __send_text(self, chat_id: int, message: str) -> typing.Dict:
        payload = {
            'chat_id': str(chat_id),
            'text': message,
        }
        logger.debug(('token:', self.bot_token), ('chatid:', chat_id))
        logger.debug(('text', message))
        logger.debug("Retrieving URL %s, payload %s", self.__text_message_url, payload)
        response = requests.request("POST", self.__text_message_url, data=payload)
        logger.debug("Got response (%i): %s", response.status_code, response.content)
        data = response.json()

        # handle error
        if response.status_code != 200:
            self.__handle_error("When sending bot text message, we got an error.", response, chat_id)

        return data.get('result', {})

    def __send_images(self, chat_id: int, msg: Union[None, typing.Dict], images: typing.List[str]):
        """
        Send image to given user id (receiver).
        If msg is not None, it will send the images as a response to given message
        :param chat_id: the user/group that will receive the image
        :param msg: message that will be replied to
        :param images: list of urls
        :return: None
        """

        payload = {
            'chat_id': str(chat_id),
            # media expected to be an array of objects in string format
            'media': json.dumps([{"type": "photo", "media": url} for url in images[:min(10, len(images))]]),
            'disable_notification': True,
        }
        if msg.get('message_id', None):
            payload['reply_to_message_id'] = msg.get('message_id')

        response = requests.request("POST", self.__media_group_url, data=payload)

        if response.status_code != 200:
            self.__handle_error("When sending media group, we got an error.", response=response, chat_id=str(chat_id))

    def __handle_error(self, msg: str, response, chat_id) -> None:
        """
        Handles telegram API error responses
        :param msg: the message for logging
        :param response: the response that is received form the API
        :param chat_id: the receiver that was supposed to get the message
        :return: None

        :raise BotBlockedException: Happens when bot trys to send a message to a user that has already blocked the bot
        :raise UserDeactivatedException: Happens when bot try to send a message to a deactivated user
        """
        status_code = response.status_code
        data = response.json()

        logger.error(f"{msg}, status code: %i, data: %s", status_code, data)

        if response.status_code == 403:
            if "bot was blocked by the user" in data.get("description", ""):
                raise BotBlockedException("User %i blocked the bot" % chat_id)
            if "user is deactivated" in data.get("description", ""):
                raise UserDeactivatedException("User %i has been deactivated" % chat_id)

    def __get_images(self, expose: typing.Dict) -> typing.List[str]:
        return expose.get("images", [])

    def __get_text_message(self, expose: typing.Dict) -> str:
        """
        Build text message based on the exposed data
        :param expose: dictionary
        :return: str
        """

        return self.config.message_format().format(
            title=expose.get('title', 'N/A'),
            rooms=expose.get('rooms', 'N/A'),
            size=expose.get('size', 'N/A'),
            price=expose.get('price', 'N/A'),
            url=expose.get('url', 'N/A'),
            address=expose.get('address', 'N/A'),
            durations=expose.get('durations', 'N/A')
        ).strip()
