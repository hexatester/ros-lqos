from typing import List

from .config import MIKROTIKS, PARENTS, HEADER
from .ppp import make_shaped_ppp
from .dhcp import make_shaped_lease
from .queue import make_shaped_queue


def quitt():
    for _, ros in MIKROTIKS.items():
        ros.sk.close()


def main():
    results: List[str] = []
    results.extend(make_shaped_ppp())
    results.extend(make_shaped_queue())
    results.extend(make_shaped_lease())
    cpu = len(PARENTS) - 1
    finals = [HEADER]
    for line in results:
        finals.append(line.replace("XPARENT", PARENTS[cpu]))
        if cpu == 0:
            cpu = len(PARENTS)
        cpu -= 1
    return "\n".join(finals)


if __name__ == "__main__":
    print(main())
    quitt()
