""" dummy portal filter

    Implements the portal filter API yet doing nothing.
    Usefull for web-app development """

import logging

logging.basicConfig()
logger = logging.getLogger("dummy-filter")


def initial_setup(**kwargs):
    logger.info(f"called initial_setup with {kwargs=}")
    ...


def ack_client_registration(**kwargs):
    logger.info(f"called ack_client_registration with {kwargs=}")
    ...


def get_identifier_for(**kwargs) -> str:
    logger.info(f"called get_identifier_for with {kwargs=}")
    return "aa:bb:cc:dd:ee:ff"


def is_client_active(**kwargs) -> bool:
    logger.info(f"called get_identifier_for with {kwargs=}")
    return False
