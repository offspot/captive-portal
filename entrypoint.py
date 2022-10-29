#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import os
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent.resolve()))

from portal.constants import Conf
from portal.web import app

if not os.getenv("DONT_SETUP_FILTER"):
    Conf.logger.info(f"setting up filter via {Conf.filter_module}")
    initial_setup = Conf.get_filter_func("initial_setup")
    initial_setup()

if __name__ == "__main__":
    app.run(host=os.getenv("BIND_TO", "127.0.0.1"), port=int(os.getenv("PORT", 3000)))
else:
    application = app
