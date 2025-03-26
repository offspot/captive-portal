"""netfilter-based captive-portal mechanism

PARAMS:
    - HOSTPOT_IP environ to redirect captured http(s) requests to
    - CAPTURED_NETWORKS environ to restrict capture to specific networks

Behavior:
- http(s) packets from captured net and not for hotspot are sent to captive_x chain
- if source ip is in captive_passlist chain, it is accepted
- if not, its redirected to hotspot:2080/2443

Portal UI calls back once its user is *registered* and we add its IP to passlist

A periodic clean-up of passlist is expected as device-clients are expected
to be used by various users over time
"""

import collections
import ipaddress
import json
import logging
import os
import pathlib
import platform
import subprocess
import time
from typing import List, Optional, Tuple

if platform.system() != "Linux":
    raise NotImplementedError(f"{platform.system()} is not supported. Linux only")

import nftables

try:
    import scapy.all
except OSError as exc:
    print(f"{exc} -- RETRYING")
    time.sleep(5)
    import scapy.all


logging.basicConfig(level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO)
logger = logging.getLogger("portal-filter")

PORTAL_IP: str = os.getenv("HOTSPOT_IP", "192.168.2.1")
HTTP_PORT: int = int(os.getenv("HTTP_PORT", "2080"))
HTTPS_PORT: int = int(os.getenv("HTTP_PORT", "2443"))
CAPTURED_NETWORKS: List[str] = os.getenv("CAPTURED_NETWORKS", "").split("|")
CAPTURED_ADDRESS: str = os.getenv("CAPTURED_ADDRESS", "") or "198.51.100.1/32"

INTERNET_STATUS_FILE = pathlib.Path("/var/run/internet")

######################
# portal-filter API: start
######################


def initial_setup(**kwargs):
    """call setup_capture if there is no CAPTIVE_PASSLIST chain (assume not setup)"""
    result = query_netfilter("list chain nat CAPTIVE_PASSLIST")
    if not result.succeeded:
        return setup_capture(hotspot_ip=PORTAL_IP, captured_networks=CAPTURED_NETWORKS)
    return True, []


# API
def ack_client_registration(ip_addr: str) -> bool:
    """whether ip_addr has been added to CAPTIVE_PASSLIST chain (if not present)

    rule is INSERTED so it's passed before the end-of-chain's RETURN
    but AFTER the first two rules that allow CAPTURED_ADDRESS to work"""

    # check that it's not already present
    if ip_in_passlist(ip_addr):
        return False

    result = query_netfilter(
        f"insert rule ip nat CAPTIVE_PASSLIST index 2 ip saddr {ip_addr} "
        + 'counter accept comment "allow host"'
    )
    return result.succeeded


# API
def get_identifier_for(ip_addr: str, default="aa:bb:cc:dd:ee:ff") -> str:
    """return MAC address (using ARP) of (last) device set to ip_addr"""
    if not is_valid_ip(ip_addr):
        return default

    try:
        return scapy.all.getmacbyip(ip_addr) or default
    except Exception as exc:
        logger.debug(f"Failed to get HW addr for {ip_addr}: {exc}")
        return default


# API
def is_client_active(ip_addr: str) -> bool:
    """whether one can consider this client active"""
    if not is_valid_ip(ip_addr):
        return False

    return has_active_connection(ip_addr)


######################


def system_is_online() -> bool:
    """whether system has internet connectivity"""
    try:
        return INTERNET_STATUS_FILE.read_text().strip() == "online"
    except Exception as exc:
        logger.error(f"cannot read connectivity status: {exc}")
        return False


class NftResult(collections.namedtuple("NftResult", ["rc", "output", "error"])):
    @property
    def succeeded(self):
        return self.rc == 0

    @property
    def json(self):
        return json.loads(self.output)


def is_valid_ip(ip_addr: str) -> bool:
    """whether IP address string is a valid IPv4"""
    try:
        ipaddress.IPv4Address(ip_addr)
    except Exception:
        return False
    return True


def query_netfilter(command: str) -> NftResult:
    """Result of executing a netfilter command"""
    nft = nftables.Nftables()
    nft.set_json_output(True)

    return NftResult(*nft.cmd(command))


def query_netfilter_bulk(commands: List[str]) -> Tuple[bool, List[NftResult]]:
    """Result of executing a list of netfilter commands with global success bool"""
    nft = nftables.Nftables()
    nft.set_json_output(True)

    results = []
    for command in commands:
        results.append(NftResult(*nft.cmd(command)))

    return all([res.succeeded for res in results]), results


def ip_in_passlist(ip_addr: str) -> str:
    """whether ip_addr has its accept rule in our passlist"""
    if not is_valid_ip(ip_addr):
        return ""
    result = query_netfilter("list chain nat CAPTIVE_PASSLIST")
    if not result.succeeded:
        return ""

    for entry in result.json.get("nftables", []):
        if entry.get("rule", {}).get("comment") != "allow host":
            continue
        if entry["rule"]["expr"][0]["match"] == {
            "op": "==",
            "left": {"payload": {"protocol": "ip", "field": "saddr"}},
            "right": str(ip_addr),
        }:
            return entry["rule"]["handle"]
    return ""


def setup_capture(hotspot_ip: str, captured_networks: List[str]):
    """install our table, chains and rules"""
    rules = []

    # should already be present
    rules.append("add table ip nat")

    # create chains (CAPTIVE_HTTP, CAPTIVE_HTTPS, CAPTIVE_PASSLIST)
    for chain in ("PREROUTING", "CAPTIVE_HTTP", "CAPTIVE_HTTPS", "CAPTIVE_PASSLIST"):
        rules.append(f"add chain ip nat {chain}")

    if not captured_networks:
        rules.append(
            f"add rule ip nat PREROUTING ip daddr != {hotspot_ip} tcp "
            + "dport 80 counter jump CAPTIVE_HTTP "
            + 'comment "Captured HTTP traffic to CAPTIVE_HTTP"'
        )
        rules.append(
            f"add rule ip nat PREROUTING ip daddr != {hotspot_ip} tcp "
            + "dport 443 counter jump CAPTIVE_HTTPS "
            + 'comment "Captured HTTPS traffic to CAPTIVE_HTTPS"'
        )
    else:
        # Forward HTTP(s) traffic on captured network to CAPTIVE_HTTP(s)
        for network in captured_networks:
            # add rule ip nat PREROUTING ip saddr 192.168.2.128/25 \
            # ip daddr != 192.168.2.1 tcp dport 80 counter jump CAPTIVE_HTTP
            rules.append(
                f"add rule ip nat PREROUTING ip saddr {network} tcp "
                + "dport 80 counter jump CAPTIVE_HTTP "
                + 'comment "Captured HTTP traffic to CAPTIVE_HTTP"'
            )
            rules.append(
                f"add rule ip nat PREROUTING ip saddr {network} tcp "
                + "dport 443 counter jump CAPTIVE_HTTPS "
                + 'comment "Captured HTTPS traffic to CAPTIVE_HTTPS"'
            )

    # Move from CAPTIVE_HTTP(s) to CAPTIVE_PASSLIST
    for chain in ("CAPTIVE_HTTP", "CAPTIVE_HTTPS"):
        rules.append(
            f"add rule ip nat {chain} ip protocol tcp "
            + "counter jump CAPTIVE_PASSLIST "
            + 'comment "Jump to CAPTIVE_PASSLIST to try to escape filtering"'
        )

    # DNAT from CAPTIVE_HTTP(s) to hotspot_ip:80/443
    for chain, port in (("CAPTIVE_HTTP", HTTP_PORT), ("CAPTIVE_HTTPS", HTTPS_PORT)):
        rules.append(
            f"add rule ip nat {chain} ip protocol tcp "
            + f"counter dnat to {hotspot_ip}:{port} "
            + f'comment "redirect HTTP(s) traffic to hotspot server port {port}"'
        )

    # make sure to return if targetting captured_address before the accept rules
    # per client. Those must be the first two rules (indexes 0 and 1)
    rules.append(
        f"add rule ip nat CAPTIVE_PASSLIST ip daddr {CAPTURED_ADDRESS} tcp dport 80 "
        + 'counter return comment "return derived addr to calling chain (captive_http)"'
    )
    rules.append(
        f"add rule ip nat CAPTIVE_PASSLIST ip daddr {CAPTURED_ADDRESS} tcp dport 443 "
        + 'counter return comment "return derived addr to calling chain (captive_https)"'
    )

    # registered host have an inserted rule in CAPTIVE_PASSLIST to ACCEPT based on IP
    # RETURN to calling chain at end of CAPTIVE_PASSLIST
    rules.append(
        "add rule ip nat CAPTIVE_PASSLIST ip protocol tcp "
        + 'counter return comment "return non-accepted to calling chain (captive_httpx)"'
    )

    return query_netfilter_bulk(rules)


def has_active_connection(ip_addr: str) -> bool:
    r"""whether there is at least one established connection for this IP

    /!\ depends on `conntrack` binary being installed and will silently
    report non-active if missing.

    /!\ active doesn't necessarily mean that the user behind the device is
    actively using the network. Most device nowadays (especially mobile)
    have OS or services phoning home regularily so it's likely a connected device
    will always appear active as long as it's connected to the network

    https://github.com/ei-grad/python-conntrack
    """
    if not is_valid_ip(ip_addr):
        return False
    ps = subprocess.run(
        [
            "/usr/bin/env",
            "conntrack",
            "--dump",
            "--src",
            f"{ip_addr}",
            "--proto",
            "tcp",
            "--state",
            "ESTABLISHED",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(ps.returncode == 0 and ps.stdout.strip())


def clear_passlist(inactives_only: Optional[bool] = True):
    """remove all registered IPs from CAPTIVE_PASSLIST chain or innactives only"""

    # list of (delete) rules we'll fill-up
    rules = []

    result = query_netfilter("list chain nat CAPTIVE_PASSLIST")
    if not result.succeeded:
        return
    for entry in result.json.get("nftables", []):
        if entry.get("rule", {}).get("comment") != "allow host":
            continue
        handle = entry["rule"]["handle"]
        ip = entry["rule"].get("expr", [{}])[0].get("match", {}).get("right")
        if not ip:
            continue

        rule = f"delete rule ip nat CAPTIVE_PASSLIST handle {handle}"
        if not inactives_only or not has_active_connection(ip):
            rules.append(rule)
    if rules:
        return query_netfilter_bulk(rules)
    return True, []


def remove_from_passlist(ip_addr: str) -> bool:
    """whether ip_addr has been removed from passlist"""
    if not is_valid_ip(ip_addr):
        return False

    handle = ip_in_passlist(ip_addr)
    if not handle:
        return False

    return query_netfilter(
        f"delete rule ip nat CAPTIVE_PASSLIST handle {handle}"
    ).succeeded
