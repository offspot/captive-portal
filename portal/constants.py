import importlib
import logging
import os
import pathlib
from dataclasses import dataclass
from typing import Callable

logging.basicConfig(level=logging.INFO)


@dataclass
class Config:
    # user-defined variables
    name: str = os.getenv("HOTSPOT_NAME", "default")
    fqdn: str = os.getenv("HOTSPOT_FQDN", "default.hotspot")
    timeout_mn: int = int(os.getenv("TIMEOUT", "60"))  # 1h default
    footer_note: str = os.getenv("FOOTER_NOTE")

    # impl & debug
    debug: bool = os.getenv("DEBUG", False)
    db_path: pathlib = pathlib.Path(os.getenv("DB_PATH", "portal-users.db"))
    filter_module: str = os.getenv("FILTER_MODULE", "dummy_portal_filter")

    # internal
    logger: logging.Logger = logging.getLogger("home-portal")
    root: pathlib.Path = pathlib.Path(__file__).parent
    _filter_module: Callable = None

    def __post_init__(self):
        if self.debug:
            self.logger.setLevel(logging.DEBUG)

        if self.filter_module:
            self.logger.info(f"importing {self.filter_module} into _filter_module")
            self._filter_module = importlib.import_module(self.filter_module)

    @property
    def timeout(self):
        """timeout in seconds"""
        return self.timeout_mn * 60

    def get_filter_func(self, name: str):
        return getattr(self._filter_module, name)


Conf = Config()
