import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from .config import MIKROTIKS, DOWNLOAD, UPLOAD

logger = logging.getLogger(__name__)


@dataclass
class Lease:
    address: str
    mac_address: str
    comment: Optional[str] = None
    routes: Optional[str] = None
    rate_limit: Optional[str] = None

    @classmethod
    def from_line(cls, line: Tuple[str, dict]) -> Optional["Lease"]:
        try:
            _, data = line
            res = cls(data["=address"], data["=mac-address"])
            if "=comment" in data:
                res.comment = data["=comment"]
            if "=routes" in data:
                res.routes = data["=routes"]
            if "=rate-limit" in data:
                res.rate_limit = data["=rate-limit"]
            return res
        except:
            pass
        return None

    @classmethod
    def from_res(cls, responses: List[tuple]):
        results = list()
        for line in responses:
            res = cls.from_line(line)
            if res is not None:
                results.append(res)
        return results


@dataclass
class Queue:
    name: str
    target: str
    comment: Optional[str] = None
    max_limit: Optional[str] = None
    limit_at: Optional[str] = None
    parent: Optional[str] = None
    dmax: int = DOWNLOAD
    umax: int = UPLOAD
    dmin: int = 1
    umin: int = 1

    def __post_init__(self):
        if self.limit_at:
            try:
                u, d = self.limit_at.split("/")
                u, d = int(u) // 1000000, int(d) // 1000000
                if u > 0:
                    self.umin = u
                if d > 0:
                    self.umin = d
            except:
                pass
        if self.max_limit:
            try:
                u, d = self.max_limit.split("/")
                u, d = int(u) // 1000000, int(d) // 1000000
                if u > 0 and u > self.umin:
                    self.umax = u
                if d > 0 and d > self.dmin:
                    self.dmax = d
            except:
                pass

    @classmethod
    def from_line(cls, line: Tuple[str, dict]) -> Optional["Queue"]:
        try:
            _, data = line
            res = cls(data["=name"], data["=target"])
            if "=comment" in data:
                res.comment = data["=comment"]
            if "=max-limit" in data:
                res.max_limit = data["=max-limit"]
            if "=limit-at" in data:
                res.limit_at = data["=limit-at"]
            if "=parent" in data:
                res.parent = data["=parent"]
            return res
        except:
            pass
        return None

    @classmethod
    def from_res(cls, responses: List[tuple]):
        results = list()
        for line in responses:
            res = cls.from_line(line)
            if res is not None:
                results.append(res)
        return results


@dataclass
class PPPoE:
    name: str
    address: str
    caller_id: str

    @classmethod
    def from_line(cls, line: Tuple[str, dict]) -> Optional["PPPoE"]:
        try:
            _, data = line
            return cls(data["=name"], data["=address"], data["=caller-id"])
        except:
            pass
        return None

    @classmethod
    def from_res(cls, responses: List[tuple]):
        results = list()
        for line in responses:
            res = cls.from_line(line)
            if res is not None:
                results.append(res)
        return results


@dataclass
class PPPSecret:
    name: str
    remote_address: str
    profile: str
    mac_address: str = ""
    routes: str = ""
    comment: str = ""

    @classmethod
    def from_line(cls, line: Tuple[str, dict]) -> Optional["PPPSecret"]:
        try:
            _, data = line
            res = cls(data["=name"], data["=remote-address"], data["=profile"])
            if "=routes" in data:
                res.routes = data["=routes"]
            if "=comment" in data:
                res.comment = data["=comment"]
            return res
        except:
            pass
        return None

    @classmethod
    def from_res(cls, responses: List[tuple]):
        results = list()
        for line in responses:
            res = cls.from_line(line)
            if res is not None:
                results.append(res)
        return results


@dataclass
class PPPProfile:
    name: str
    rate_limit: Optional[str] = None
    parent_queue: Optional[str] = None

    @classmethod
    def from_line(cls, line: Tuple[str, dict]) -> Optional["PPPProfile"]:
        try:
            _, data = line
            res = cls(data["=name"])
            if "=rate-limit" in data:
                res.rate_limit = data["=rate-limit"]
            if "=parent-queue" in data:
                res.parent_queue = data["=parent-queue"]
            return res
        except:
            pass
        return None

    @classmethod
    def from_res(cls, responses: List[tuple]):
        results = list()
        for line in responses:
            res = cls.from_line(line)
            if res is not None:
                results.append(res)
        return results


def get_leases(nodisabled=True):
    results = dict()
    say = [
        "/ip/dhcp-server/lease/print",
        "=.proplist=address,mac-address,comment,routes,rate-limit",
    ]
    if nodisabled:
        say.append("?=disabled=no")
    for addr, api in MIKROTIKS.items():
        results[addr] = dict()
        responses = api.talk(say)
        lease: Lease
        for lease in Lease.from_res(responses):
            results[addr][lease.address] = lease
    return results


def get_pppsecrets():
    results = dict()
    for addr, api in MIKROTIKS.items():
        results[addr] = dict()
        responses = api.talk(
            [
                "/ppp/secret/print",
                "=.proplist=name,remote-address,routes,profile,comment",
            ]
        )
        pppoe: PPPSecret
        for pppoe in PPPSecret.from_res(responses):
            results[addr][pppoe.remote_address] = pppoe
    return results


def get_pppoes():
    results = dict()
    for addr, api in MIKROTIKS.items():
        results[addr] = dict()
        responses = api.talk(["/ppp/active/print", "=.proplist=name,address,caller-id"])
        pppoe: PPPoE
        for pppoe in PPPoE.from_res(responses):
            results[addr][pppoe.address] = pppoe
    return results


def get_pppprofiles():
    results = dict()
    for addr, api in MIKROTIKS.items():
        results[addr] = dict()
        responses = api.talk(
            ["/ppp/profile/print", "=.proplist=name,rate-limit,parent-queue"]
        )
        pppoe: PPPProfile
        for pppoe in PPPProfile.from_res(responses):
            results[addr][pppoe.name] = pppoe
    return results


def get_queues():
    results = dict()
    for addr, api in MIKROTIKS.items():
        results[addr] = dict()
        responses = api.talk(
            [
                "/queue/simple/print",
                "=.proplist=name,target,max-limit,limit-at,comment,parent",
            ]
        )
        queue: Queue
        for queue in Queue.from_res(responses):
            results[addr][queue.name] = queue
    return results


LEASES: Dict[str, Dict[str, Lease]] = get_leases()
SECRETS: Dict[str, Dict[str, PPPSecret]] = get_pppsecrets()
PPPOES: Dict[str, Dict[str, PPPoE]] = get_pppoes()
PROFILES: Dict[str, Dict[str, PPPProfile]] = get_pppprofiles()
QUEUES: Dict[str, Dict[str, Queue]] = get_queues()
