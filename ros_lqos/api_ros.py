#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import binascii
import socket
import select
import ssl
import hashlib
import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


SENSITIVE_PATTERNS = re.compile(r"(=password=|=response=)(.+)", re.IGNORECASE)


def mask_sensitive(word):
    """Mask sensitive data in API words for logging"""
    return SENSITIVE_PATTERNS.sub(r"\1***", word)


class ApiRos:
    """RouterOS API client"""

    def __init__(self, sk: socket.socket):
        self.sk = sk
        self._username = ""
        self._password = ""
        self.address = ""

    def login(self, username, pwd):
        if not self._username:
            self._username = username
        if not self._password:
            self._password = pwd
        return self._login()

    def _login(self):
        for repl, attrs in self.talk(
            ["/login", "=name=" + self._username, "=password=" + self._password]
        ):
            if repl == "!trap":
                return False
            elif "=ret" in attrs:
                # Legacy authentication (RouterOS < 6.43)
                chal = binascii.unhexlify((attrs["=ret"]).encode("utf-8"))
                md = hashlib.md5()
                md.update(b"\x00")
                md.update(self._password.encode("utf-8"))
                md.update(chal)
                for repl2, attrs2 in self.talk(
                    [
                        "/login",
                        "=name=" + self._username,
                        "=response=00" + binascii.hexlify(md.digest()).decode("utf-8"),
                    ]
                ):
                    if repl2 == "!trap":
                        return False
        return True

    def talk(self, words):
        if self.writeSentence(words) == 0:
            return []
        r = []
        while True:
            i = self.readSentence()
            if len(i) == 0:
                continue
            reply = i[0]
            attrs = {}
            for w in i[1:]:
                j = w.find("=", 1)
                if j == -1:
                    attrs[w] = ""
                else:
                    attrs[w[:j]] = w[j + 1 :]
            r.append((reply, attrs))
            if reply == "!done":
                return r

    def writeSentence(self, words):
        ret = 0
        for w in words:
            self.writeWord(w)
            ret += 1
        self.writeWord("")
        return ret

    def readSentence(self):
        r = []
        while True:
            w = self.readWord()
            if w == "":
                return r
            r.append(w)

    def writeWord(self, w):
        # print("<<< " + mask_sensitive(w))
        data = w.encode("utf-8")
        self.writeLen(len(data))
        self.writeBytes(data)

    def readWord(self):
        ret = self.readStr(self.readLen())
        # print(">>> " + mask_sensitive(ret))
        return ret

    def writeLen(self, l):
        if l < 0x80:
            self.writeBytes(l.to_bytes(1, "big"))
        elif l < 0x4000:
            self.writeBytes((l | 0x8000).to_bytes(2, "big"))
        elif l < 0x200000:
            self.writeBytes((l | 0xC00000).to_bytes(3, "big"))
        elif l < 0x10000000:
            self.writeBytes((l | 0xE0000000).to_bytes(4, "big"))
        else:
            self.writeBytes(b"\xf0" + l.to_bytes(4, "big"))

    def readLen(self):
        c = ord(self.readBytes(1))
        if (c & 0x80) == 0x00:
            pass
        elif (c & 0xC0) == 0x80:
            c &= ~0xC0
            c <<= 8
            c += ord(self.readBytes(1))
        elif (c & 0xE0) == 0xC0:
            c &= ~0xE0
            c <<= 8
            c += ord(self.readBytes(1))
            c <<= 8
            c += ord(self.readBytes(1))
        elif (c & 0xF0) == 0xE0:
            c &= ~0xF0
            c <<= 8
            c += ord(self.readBytes(1))
            c <<= 8
            c += ord(self.readBytes(1))
            c <<= 8
            c += ord(self.readBytes(1))
        elif (c & 0xF8) == 0xF0:
            c = ord(self.readBytes(1))
            c <<= 8
            c += ord(self.readBytes(1))
            c <<= 8
            c += ord(self.readBytes(1))
            c <<= 8
            c += ord(self.readBytes(1))
        return c

    def writeBytes(self, data):
        """Write raw bytes to socket"""
        n = 0
        while n < len(data):
            r = self.sk.send(data[n:])
            if r == 0:
                raise RuntimeError("connection closed by remote end")
            n += r

    def readBytes(self, length):
        """Read exact number of bytes from socket"""
        ret = b""
        while len(ret) < length:
            s = self.sk.recv(length - len(ret))
            if s == b"":
                raise RuntimeError("connection closed by remote end")
            ret += s
        return ret

    def readStr(self, length):
        """Read string of specified length from socket"""
        data = self.readBytes(length)
        return data.decode("utf-8", errors="replace")


def parse_bool(value):
    """Parse string to boolean"""
    return value.lower() in ("true", "1", "yes", "on")


def parse_port(value):
    """Parse and validate port number"""
    try:
        port = int(value)
    except ValueError:
        raise ValueError(f"Invalid port number: {value}")
    if not 1 <= port <= 65535:
        raise ValueError(f"Port must be between 1 and 65535, got {port}")
    return port


def open_socket(dst, port, secure=False, verify_ssl=False):
    """Open socket connection to RouterOS device"""
    res = socket.getaddrinfo(dst, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    af, socktype, proto, canonname, sockaddr = res[0]
    s = socket.socket(af, socktype, proto)

    try:
        if secure:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            if verify_ssl:
                context.verify_mode = ssl.CERT_REQUIRED
                context.load_default_certs()
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            s = context.wrap_socket(s, server_hostname=dst)
        s.connect(sockaddr)
        return s
    except:
        s.close()
        raise


def connect_ros(dst, port, secure, verify_ssl) -> Optional[ApiRos]:
    try:
        s = open_socket(dst, port, secure, verify_ssl)
    except socket.gaierror as e:
        logger.warning(f"Error: Could not resolve hostname '{dst}': {e}")
        return None
    except socket.error as e:
        logger.warning(f"Error: Could not connect to {dst}:{port}: {e}")
        return None
    except ssl.SSLError as e:  # type: ignore
        logger.warning(f"Error: SSL connection failed: {e}")
        return None
    return ApiRos(s)


def login_ros(device: str, user: str, passw: str) -> Optional[ApiRos]:
    apiros = connect_ros(dst=device, port=8728, secure=False, verify_ssl=False)
    if apiros is None:
        return None
    if not apiros.login(user, passw):
        # print("Error: Login failed")
        apiros.sk.close()
        return None
    apiros.address = device
    return apiros


def make_ros(mikrotiks) -> List[ApiRos]:
    rose = list()
    for konfig in str(mikrotiks).split(","):
        device, user, passw = konfig.split(";")
        rosd = login_ros(device, user, passw)
        if rosd is None:
            continue
        rose.append(rosd)
    return rose


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    dst = sys.argv[1]
    user = "admin"
    passw = ""
    secure = False
    port = 0
    verify_ssl = False

    arg_nr = len(sys.argv)

    if arg_nr > 2:
        user = sys.argv[2]
    if arg_nr > 3:
        passw = sys.argv[3]
    if arg_nr > 4:
        secure = parse_bool(sys.argv[4])
    if arg_nr > 5:
        try:
            port = parse_port(sys.argv[5])
        except ValueError as e:
            # print(f"Error: {e}")
            sys.exit(1)
    if arg_nr > 6:
        verify_ssl = parse_bool(sys.argv[6])

    if port == 0:
        port = 8729 if secure else 8728

    try:
        s = open_socket(dst, port, secure, verify_ssl)
    except socket.gaierror as e:
        print(f"Error: Could not resolve hostname '{dst}': {e}")
        sys.exit(1)
    except socket.error as e:
        print(f"Error: Could not connect to {dst}:{port}: {e}")
        sys.exit(1)
    except ssl.SSLError as e:  # type: ignore
        print(f"Error: SSL connection failed: {e}")
        sys.exit(1)

    apiros = ApiRos(s)

    if not apiros.login(user, passw):
        print("Error: Login failed")
        s.close()
        sys.exit(1)

    print(f"Connected to {dst}:{port} as {user}")
    print("Enter API commands (empty line to send, Ctrl+C to exit)")

    inputsentence = []

    try:
        while True:
            r = select.select([s, sys.stdin], [], [], None)
            if s in r[0]:
                apiros.readSentence()

            if sys.stdin in r[0]:
                # Read line from input and strip newline
                l = sys.stdin.readline()
                if l == "":
                    # EOF reached
                    break
                l = l.rstrip("\n\r")

                # Empty line sends the sentence
                if l == "":
                    if inputsentence:
                        apiros.writeSentence(inputsentence)
                        inputsentence = []
                else:
                    inputsentence.append(l)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        s.close()


if __name__ == "__main__":
    main()
