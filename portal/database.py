import datetime
from typing import Any, Dict, Optional

import peewee

from portal.constants import Conf

Conf.db_path.parent.mkdir(parents=True, exist_ok=True)
portal_db = peewee.SqliteDatabase(str(Conf.db_path))
is_client_active = Conf.get_filter_func("is_client_active")


class User(peewee.Model):
    class Meta:
        database = portal_db

    # ident-related fields
    hw_addr = peewee.CharField(primary_key=True)
    ip_addr = peewee.IPField()

    # metadata
    platform = peewee.CharField(null=True)
    system = peewee.CharField(null=True)
    system_version = peewee.FloatField(null=True)
    browser = peewee.CharField(null=True)
    browser_version = peewee.FloatField(null=True)
    language = peewee.CharField(null=True)

    # registration-related fields
    last_seen_on = peewee.DateTimeField(default=datetime.datetime.now)
    registered_on = peewee.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        self.last_seen_on = datetime.datetime.now()
        return super().save(*args, **kwargs)

    @property
    def is_registered(self) -> bool:
        if not self.registered_on:
            return False
        now = datetime.datetime.now()
        return (
            now > self.registered_on
            and (now - self.registered_on).total_seconds() < Conf.timeout
        )

    @property
    def is_active(self) -> bool:
        return is_client_active(ip_addr=self.ip_addr)

    @property
    def is_apple(self) -> bool:
        return self.platform.lower() in ("apple", "macos", "iphone", "ipad")

    def register(self, delay: Optional[int] = 0):
        self.registered_on = datetime.datetime.now() + datetime.timedelta(seconds=delay)
        self.save()

    @classmethod
    def create_or_update(cls, hw_addr: str, ip_addr: str, extras: Dict[str, Any]):
        data = {"ip_addr": ip_addr, "last_seen_on": datetime.datetime.now()}
        try:
            user, created = cls.get_or_create(hw_addr=hw_addr, defaults=data)
        except peewee.IntegrityError:
            # race condition is possible
            user = cls.get(hw_addr=hw_addr)
        extras.update(data)
        for key, value in extras.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        user.save()
        return user


portal_db.create_tables([User])
