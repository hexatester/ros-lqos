from typing import List, Optional

from .config import DOWNLOAD, UPLOAD, DIV
from .api_ros import ApiRos
from .ros import (
    MIKROTIKS,
    PPPOES,
    PROFILES,
    SECRETS,
    QUEUES,
    PPPoE,
    PPPSecret,
    PPPProfile,
    Queue,
)
from .helper import ipv4_to_12digit

# "circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm""circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm"


def make_circuit_id(ros: ApiRos, pppoe: PPPoE):
    try:
        return ipv4_to_12digit(ros.address) + ipv4_to_12digit(pppoe.address)
    except Exception as e:
        raise e


def make_ipv4(pppoe: PPPoE, secret: PPPSecret):
    results = [pppoe.address]
    if secret.routes:
        for route in secret.routes.split(","):
            results.append(route.split(" ")[0])
    return ",".join(results)


def make_ipv6():
    return ""


def make_speed(profile: PPPProfile, queue: Optional[Queue] = None):
    # "download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps"
    dmin = 1
    umin = 1
    dmax = DOWNLOAD
    umax = UPLOAD
    if queue and queue.max_limit and queue.limit_at:
        # 8M/8M 0/0 0/0 0/0 6 4M/4M
        umax, dmax = queue.max_limit.replace("M", "").split("/")
        umin, dmin = queue.limit_at.replace("M", "").split("/")
    if queue and queue.max_limit:
        u, d = queue.max_limit.replace("M", "").split("/")
        dmax = int(d)
        dmin = dmax // DIV
        umax = int(u)
        umin = umax // DIV
    elif not profile.rate_limit:
        pass
    elif " " in profile.rate_limit:
        # 8M/8M 0/0 0/0 0/0 6 4M/4M
        rates = profile.rate_limit.split(" ")
        assert len(rates) == 6
        umax, dmax = rates[0].replace("M", "").split("/")
        umin, dmin = rates[-1].replace("M", "").split("/")
    else:
        u, d = profile.rate_limit.replace("M", "").split("/")
        dmax = int(d)
        dmin = dmax // DIV
        umax = int(u)
        umin = umax // DIV
    return (str(dmin), str(umin), str(dmax), str(umax))


def make_shaped_line(name: str, user: str, pppoe: PPPoE):
    secret = SECRETS[name][user]
    profile = PROFILES[name][secret.profile]
    api = MIKROTIKS[name]
    queue = QUEUES[name].get(secret.name)
    try:
        _results: List[str] = [
            make_circuit_id(api, pppoe),
            secret.comment or f"{secret.name} {secret.profile}",
            ipv4_to_12digit(pppoe.address),
            secret.name,
            "XPARENT",
            pppoe.caller_id,
            make_ipv4(pppoe, secret),
            make_ipv6(),
            *make_speed(profile, queue),
        ]
    except Exception as e:
        raise e
    results = list()
    for result in _results:
        res = result.replace(",", "\\,")
        res = result.replace('"', '\\"')
        results.append(f'"{res}"')
    return ",".join(results)


def make_shaped_ppp():
    results: List[str] = list()
    for name, actives in PPPOES.items():
        for user, pppoe in actives.items():
            result = make_shaped_line(name, user, pppoe)
            if result:
                results.append(result)
    return results
