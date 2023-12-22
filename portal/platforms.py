import flask

from portal.constants import Conf

logger = Conf.logger

APPLE_HOSTS = [
    "captive.apple.com",
    "appleiphonecell.com",
    "*.apple.com.edgekey.net",
    "gsp1.apple.com",
    "apple.com",
    "www.apple.com",
    "iphone-ld.apple.com",
    "netcts.cdn-apple.com",
]

MICROSOFT_HOSTS = [
    "ipv6.msftncsi.com",
    "detectportal.firefox.com",
    "ipv6.msftncsi.com.edgesuite.net",
    "www.msftncsi.com",
    "www.msftncsi.com.edgesuite.net",
    "www.msftconnecttest.com",
    "www.msn.com",
    "teredo.ipv6.microsoft.com",
    "teredo.ipv6.microsoft.com.nsatc.net",
    "ctldl.windowsupdate.com",
]

GOOGLE_HOSTS = [
    "clients3.google.com",
    "mtalk.google.com",
    "alt7-mtalk.google.com",
    "alt6-mtalk.google.com",
    "connectivitycheck.android.com",
    "connectivitycheck.gstatic.com",
    "developers.google.cn",
    "play.googleapis.com",
]

LINUX_HOSTS = ["connectivity-check.ubuntu.com", "nmcheck.gnome.org"]

FIREFOX_HOSTS = ["detectportal.firefox.com"]


def is_google_request(request):
    return request.path == "/gen_204" or request.path == "/generate_204"


def is_apple_request(request):
    return request.host in APPLE_HOSTS


def is_microsoft_request(request):
    return request.host in MICROSOFT_HOSTS


def is_microsoft_ncsi_request(request):
    return request.host == "www.msftncsi.com" and request.path == "/ncsi.txt"


def is_linux_request(request):
    return request.host in LINUX_HOSTS


def is_nmcheck_request(request):
    return (
        request.host == "nmcheck.gnome.org"
        and request.path == "/check_network_status.txt"
    )


def is_ubuntu_request(request):
    return request.host == "connectivity-check.ubuntu.com"


def is_firefox_request(request):
    return request.host in FIREFOX_HOSTS  # and request.path == "/success.txt"


def apple_success(request, user):
    """Fake apple Success page (200 with body containing Success)"""
    return flask.make_response(
            "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"
        )


def firefox_success(request, user):
    """`success` 200 response"""
    resp = flask.make_response(
        '<meta http-equiv="refresh" content="0;'
        'url=https://support.mozilla.org/kb/captive-portal"/>',
        200,
    )
    resp.headers["Content-Type"] = "text/html"
    return resp


def microsoft_success(request, user):
    """`Microsoft Connect Test` 200 response"""
    resp = flask.make_response("Microsoft Connect Test", 200)
    resp.headers["Content-Type"] = "text/html"
    return resp


def microsoft_success_ncsi(request, user):
    """`Microsoft NCSI` 200 response"""
    resp = flask.make_response("Microsoft NCSI", 200)
    resp.headers["Content-Type"] = "text/plain"
    return resp


def nmcheck_success(request, user):
    """`NetworkManager is online` 200 response"""
    resp = flask.make_response("NetworkManager is online\n", 200)
    resp.headers["Content-Type"] = "text/plain; charset=UTF-8"
    return resp


def ubuntu_success(request, user):
    """HTTP 1.1/204 No Content with X-NetworkManager-Status header"""
    resp = flask.make_response("", 204)
    resp.headers["X-NetworkManager-Status"] = "online"
    return resp


def google_no_content(request, user):
    """HTTP 1.1/204 No Content"""
    resp = flask.make_response("", 204)
    resp.headers["Server"] = "gws"
    return resp


def success(request, user):
    if is_apple_request(request):
        logger.debug("is_apple_request")
        return apple_success(request, user)
    elif is_firefox_request(request):
        logger.debug("is_firefox_request")
        return firefox_success(request, user)
    elif is_microsoft_request(request):
        if is_microsoft_ncsi_request(request):
            logger.debug("is_microsoft_succerequest")
            return microsoft_success_ncsi(request, user)
            logger.debug("is_microsoft_request")
        return microsoft_success(request, user)
    elif is_nmcheck_request(request):
        logger.debug("is_nmcheck_request")
        return nmcheck_success(request, user)
    elif is_ubuntu_request(request):
        logger.debug("is_ubuntu_request")
        return ubuntu_success(request, user)
    elif is_google_request(request):
        logger.debug("is_google_request")
        return google_no_content(request, user)

    # default to regular 204
    logger.debug("is_default")
    return None
