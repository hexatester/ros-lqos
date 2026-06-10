from typing import List

from .config import DOWNLOAD, UPLOAD, DIV
from .api_ros import ApiRos
from .ros import MIKROTIKS, LEASES, Lease
from .helper import ipv4_to_12digit

# "circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm""circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm"


def make_circuit_id(ros: ApiRos, lease: Lease):
    try:
        return ipv4_to_12digit(ros.address) + ipv4_to_12digit(lease.address)
    except Exception as e:
        raise e


def make_ipv4(lease: Lease):
    results = [lease.address]
    if lease.routes:
        for route in lease.routes.split(","):
            results.append(route.split(" ")[0])
    return ",".join(results)


def make_ipv6():
    return ""


def make_speed(lease: Lease):
    # "download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps"
    dmin = 1
    umin = 1
    dmax = DOWNLOAD
    umax = UPLOAD
    if not lease.rate_limit:
        pass
    elif " " in lease.rate_limit:
        # 8M/8M 0/0 0/0 0/0 6 4M/4M
        rates = lease.rate_limit.split(" ")
        assert len(rates) == 6
        umax, dmax = rates[0].replace("M", "").split("/")
        umin, dmin = rates[-1].replace("M", "").split("/")
    else:
        u, d = lease.rate_limit.replace("M", "").split("/")
        dmax = int(d)
        dmin = dmax // DIV
        umax = int(u)
        umin = umax // DIV
    return (str(dmin), str(umin), str(dmax), str(umax))


def make_shaped_line(name: str, user: str, lease: Lease):
    api = MIKROTIKS[name]
    try:
        _results: List[str] = [
            make_circuit_id(api, lease),
            lease.comment or f"{lease.mac_address} {user}",
            ipv4_to_12digit(lease.address),
            lease.comment or lease.mac_address,
            "XPARENT",
            lease.mac_address,
            make_ipv4(lease),
            make_ipv6(),
            *make_speed(lease),
        ]
    except Exception as e:
        raise e
    results = list()
    for result in _results:
        res = result.replace(",", "\\,")
        res = result.replace('"', '\\"')
        results.append(f'"{res}"')
    return ",".join(results)


def make_shaped_lease():
    results: List[str] = list()
    for name, actives in LEASES.items():
        for user, lease in actives.items():
            if lease.rate_limit:
                results.append(make_shaped_line(name, user, lease))
    return results
