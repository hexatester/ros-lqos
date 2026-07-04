def ipv4_to_12digit(ip: str) -> str:
    # Allow ,
    if "," in ip:
        ip = ip.split(",")[0]
    if "/" in ip:
        ip, _ = ip.split("/")
    octets = ip.split(".")
    if len(octets) != 4:
        raise ValueError("Invalid IPv4 address")
    return "".join(f"{int(octet):03d}" for octet in octets)
