#!/usr/bin/env python3

"""
The Unorthodox Cannonical S-Expression Parser
"""

__version__ = "0.1"

from io import StringIO, IOBase, BytesIO
from collections import namedtuple

TypeHinted = namedtuple('TypeHinted', 'hint data')

digits = (b'0', b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9')

def read_hint(fd, pos):
    hint = b''
    while True:
        ch = fd.read(1)
        pos += 1
        if ch == b']':
            return hint, pos
        else:
            hint += ch

def read_list(fd, pos):
    """Read a list"""
    out = []
    read_ahead = ""
    hint = None
    while True:
        ch = fd.read(1)
        pos += 1
        if ch == b')':
            return (out, pos)
        elif ch == b'(':
            new_list, pos = read_list(fd, pos)
            out.append(new_list)
        elif ch == b'[':
            hint, pos = read_hint(fd, pos)
        elif ch == b':':
            pos += 1
            if not read_ahead:
                raise ValueError(f"Colon but no read ahead at position {pos}")
            else:
                read_ahead = int(read_ahead)
                raw = fd.read(read_ahead)
                if hint:
                  out.append(TypeHinted(hint=hint.decode(), data=raw))
                else:
                    out.append(raw)
                pos += read_ahead
                read_ahead = ''
                hint = None
        elif ch in digits:
            read_ahead += ch.decode('ascii')
        else:
            raise ValueError(f"Unexpected {ch} at position {pos}")


def load(file):
    """Parse a file-like object"""
    out = []
    pos = 0
    ch = file.read(1)
    if not ch == b'(':
        raise ValueError("Expected start of file to begin with (")
    else:
        out, trash = read_list(file, pos)
    return out

def loadb(b):
    """Parses a bytestring"""
    f = BytesIO(b)
    return load(f)

def dump_bytes(b):
    l = len(b)
    return f"{l}:".encode() + b

def dump_string(s):
    l = len(s)
    return f"{l}:{s}".encode()

def dump_hinted(obj):
    b = dump_bytes(obj[1])
    return f"[{obj[0]}]".encode() + b

def dump_number(n):
    return dump_string(f"{n}")

def dump_sequence(seq):
    out = b''
    for obj in seq:
        if isinstance(obj, TypeHinted):
            out += dump_hinted(obj)
        elif isinstance(obj, (list, tuple)):
            out += b'(' + dump_sequence(obj) + b')'
        elif isinstance(obj, str):
            out += dump_string(obj)
        elif isinstance(obj, bytes):
            out += dump_bytes(obj)
        elif isinstance(obj, (int, float, complex)):
            out += dump_number(obj)
        else:
            raise ValueError(f"Don't know how to serialize type {type(obj)}")
    return out

def dumpb(seq):
    out = b'(' + dump_sequence(seq) + b')'
    return out

def dump(seq, fd):
    out = dump_sequence(seq)
    fd.write(seq)
