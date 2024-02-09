import re
from typing import Union

import flask
import werkzeug
from flask import Flask, Response, make_response, render_template, request
from flask_babel import Babel
from user_agents import parse

from portal.constants import Conf
from portal.database import User
from portal.platforms import success as platform_success


def get_locale():
    """select locale from HTTP Accept-Languages header value

    Dropping regional specifier as we handle offer bare-language translations"""
    supported_languages = ["fr", "es", "en"]
    try:
        return werkzeug.datastructures.LanguageAccept(
            [(al[0].split("-", 1)[0], al[1]) for al in request.accept_languages]
        ).best_match(supported_languages)
    except Exception:
        return supported_languages[-1]


logger = Conf.logger
app = Flask(Conf.logger.name, template_folder=Conf.root.joinpath("templates"))
babel = Babel(
    app,
    default_locale="en",
    default_domain="messages",
    default_translation_directories=str(Conf.root.joinpath("locale")),
    default_timezone="UTC",
    locale_selector=get_locale,
)
get_identifier_for = Conf.get_filter_func("get_identifier_for")
ack_client_registration = Conf.get_filter_func("ack_client_registration")


def std_resp(resp: Union[Response, str]) -> Response:
    if isinstance(resp, str):
        resp = make_response(resp)
    resp.headers["Cache-Control"] = "public,must-revalidate,max-age=0,s-maxage=3600"
    return resp


def get_branding_context():
    return {
        "hotspot_name": Conf.name,
        "fqdn": Conf.fqdn,
        "interval": Conf.timeout_mn,
        "footer_note": Conf.footer_note,
    }


class Request:
    def __init__(self, request):
        self.req = request

    @property
    def ip_addr(self):
        if self.req.headers.getlist("X-Forwarded-For"):
            return self.req.headers.getlist("X-Forwarded-For")[0]
        else:
            return self.req.remote_addr

    @property
    def hw_addr(self):
        return get_identifier_for(ip_addr=self.ip_addr)

    @property
    def ua(self):
        return self.req.user_agent.string

    @property
    def parsed_ua(self):
        user_agent = parse(self.ua)
        platform = None

        def other_as_none(value):
            return None if value == "Other" else value

        if re.search(r"Android", self.ua):
            platform = "android"
        if re.search(r"CaptiveNetworkSupport", self.ua):
            platform = "apple"
        if re.search(r"(OS X|iPhone OS|iPad OS)", self.ua):
            platform = platform or "apple"
        if re.search(r"(Microsoft NCSI)", self.ua):
            platform = "windows"
        if re.search(r"Windows", self.ua):
            platform = platform or "windows"
        if re.search(r"Linux", self.ua):
            platform = "linux"

        return {
            "platform": platform or str(user_agent.os.family).lower(),
            "system": other_as_none(user_agent.os.family),
            "system_version": user_agent.os.version_string or None,
            "browser": other_as_none(user_agent.browser.family),
            "browser_version": user_agent.browser.version_string or None,
            "language": (
                str(self.req.accept_languages).split(",")[0]
                if self.req.accept_languages
                else None
            ),
        }

    def get_user(self):
        return User.create_or_update(self.hw_addr, self.ip_addr, self.parsed_ua)

    def __str__(self):
        return f"{self.req.url} from {self.ip_addr}/{self.hw_addr} via {self.ua}"


def action_required(user: User) -> bool:
    """whether on a platform that will require him to copy/paste URL manually"""
    # apple brings a popup that allows link (target=_system) to open a browser
    # windows just opens a full regular browser
    return user.platform.lower() not in ("apple", "macos", "iphone", "ipad", "windows")


@app.route("/", defaults={"u_path": ""})
@app.route("/<path:u_path>")
def entrypoint(u_path):
    req = Request(request)
    logger.debug(f"IN: {req}")
    user = req.get_user()
    context = dict(
        user=user, action_required=action_required(user), **get_branding_context()
    )

    if user.is_registered and user.is_active:
        logger.debug(f"user IS registered ({user.registered_on})")
        return std_resp(
            platform_success(request, user)
            or render_template("registered.html", **context)
        )
    elif user.is_registered:
        logger.debug(f"user is registered ({user.registered_on}) but NOT ACTIVE")
    elif user.is_active:
        logger.debug("is NOT registered but IS ACTIVE")

    return std_resp(render_template("portal.html", **context))


@app.route("/fake-register")
def fake_register():
    """just display registered page, for UI testing purpose"""
    logger.debug(f"FAKE-REG: {Request(request)}")
    user = Request(request).get_user()
    context = dict(
        user=user, action_required=action_required(user), **get_branding_context()
    )
    return std_resp(render_template("registered.html", **context))


@app.route("/register")
def register():
    """record that user passed portal and should be considered online and informed"""
    logger.debug(f"REG: {Request(request)}")
    user = Request(request).get_user()
    user.register()
    ack_client_registration(ip_addr=user.ip_addr)
    context = dict(
        user=user, action_required=action_required(user), **get_branding_context()
    )
    return std_resp(render_template("registered.html", **context))


@app.route("/assets/<path:path>")
def send_static(path):
    """serve static files during devel (deployed reverseproxy)"""
    logger.debug(f"ASSETS: {Request(request)}")
    return std_resp(flask.send_from_directory(Conf.root.joinpath("assets"), path))
