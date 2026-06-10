import os
from typing import Dict

from .api_ros import connect_ros, ApiRos

HEADER = '"circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm""circuit_id","circuit_name","device_id","device_name","parent_node","mac","ipv4","ipv6","download_min_mbps","upload_min_mbps","download_max_mbps","upload_max_mbps","comment","sqm"'
ROUTEROS = os.getenv("ROUTEROS", "Ros1;192.168.0.88;8728;admin;").split("|")
CPU = int(os.getenv("CPU", "1"))
DIV = int(os.getenv("DIV", "2"))
PARENTS = os.getenv("PARENTS", "OLT1").split(",")
MIKROTIKS: Dict[str, ApiRos] = dict()
DOWNLOAD: int = int(os.getenv("DOWNLOAD", "10"))
UPLOAD: int = int(os.getenv("UPLOAD", "10"))
for r in ROUTEROS:
    name, ip, port, user, pwd = r.split(";")
    ros = connect_ros(ip, port, secure=False, verify_ssl=False)
    if not isinstance(ros, ApiRos):
        raise ValueError("Invalid env")
    if ros.login(user, pwd):
        ros.address = ip
        MIKROTIKS[name] = ros
