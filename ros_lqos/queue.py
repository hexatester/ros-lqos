from typing import List

from .config import DOWNLOAD, UPLOAD, DIV
from .api_ros import ApiRos
from .ros import MIKROTIKS, QUEUES, Queue
from .helper import ipv4_to_12digit

# "circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm""circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm"


def make_circuit_id(ros: ApiRos, queue: Queue):
    try:
        return ipv4_to_12digit(ros.address) + ipv4_to_12digit(
            queue.target.split(",")[0]
        )
    except Exception as e:
        raise e


def make_ipv4(queue: Queue):
    if "," in queue.target:
        results = queue.target.split(",")
    else:
        results = [queue.target]
    return ",".join(results)


def make_ipv6():
    return ""


def make_speed(queue: Queue):
    # "download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps"
    dmin = 1
    umin = 1
    dmax = DOWNLOAD
    umax = UPLOAD
    if not queue.max_limit:
        pass
    elif queue.limit_at:
        # 8M/8M 0/0 0/0 0/0 6 4M/4M
        umax, dmax = queue.umax, queue.dmax
        umin, dmin = queue.dmin, queue.dmax
    else:
        dmax = queue.dmax
        dmin = dmax // DIV
        umax = queue.umax
        umin = umax // DIV
    return (str(dmin), str(umin), str(dmax), str(umax))


def make_shaped_line(name: str, user: str, queue: Queue):
    api = MIKROTIKS[name]
    try:
        _results: List[str] = [
            make_circuit_id(api, queue),
            queue.comment or f"{queue.name} {queue.max_limit}",
            ipv4_to_12digit(queue.target),
            queue.comment or queue.name,
            "XPARENT",
            "",
            make_ipv4(queue),
            make_ipv6(),
            *make_speed(queue),
        ]
    except Exception as e:
        raise e
    results = list()
    for result in _results:
        res = result.replace(",", "\\,")
        res = result.replace('"', '\\"')
        results.append(f'"{res}"')
    return ",".join(results)


def valid(queue: Queue):
    try:
        for targe in queue.target.split(","):
            octets = targe.split(".")
            if len(octets) != 4:
                raise ValueError("Invalid IPv4 address")
    except ValueError:
        return False
    return True


def make_shaped_queue():
    results: List[str] = list()
    for name, actives in QUEUES.items():
        for user, queue in actives.items():
            if valid(queue) and queue.max_limit:
                results.append(make_shaped_line(name, user, queue))
    return results
