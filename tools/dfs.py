"""Acorn DFS single-sided disc image (.ssd) catalogue reading and writing.

A DFS catalogue is the first two sectors of track 0. Sector 0 holds the first
eight characters of the title and then, for each file, a seven-character name
plus a directory byte whose top bit is the "locked" flag. Sector 1 holds the
rest of the title, the cycle number, the offset of the last entry, the boot
option and disc size, and then for each file its load, exec, length and start
sector, with the 17th and 18th bits of each packed into a shared byte.
"""

from dataclasses import dataclass

SECTOR = 256
SECTORS_PER_TRACK = 10
MAX_FILES = 31


def dfs_address(addr: int) -> int:
    """The 18-bit form DFS stores of a 32-bit host address.

    Bits 16 and 17 survive; the rest of the top half is dropped, so &FFFF1900
    is stored as &31900 and &FFFFFFFF as &3FFFF."""
    return (addr & 0xFFFF) | (((addr >> 16) & 3) << 16)


@dataclass
class Entry:
    name: str  # without directory
    directory: str
    locked: bool
    load: int  # 18-bit DFS form
    exec: int
    length: int
    start: int  # sector

    @property
    def full_name(self) -> str:
        return f"{self.directory}.{self.name}"

    @property
    def sectors(self) -> int:
        return (self.length + SECTOR - 1) // SECTOR


@dataclass
class Catalogue:
    title: str
    cycle: int
    opt: int
    disc_sectors: int
    entries: list  # in catalogue order


def read_catalogue(image: bytes) -> Catalogue:
    s0, s1 = image[0:SECTOR], image[SECTOR : 2 * SECTOR]
    title = (s0[0:8] + s1[0:4]).decode("latin1").rstrip("\0 ")
    if s1[5] % 8:
        raise ValueError(f"bad catalogue: last entry offset {s1[5]:#x}")
    entries = []
    for i in range(s1[5] // 8):
        n = s0[8 + i * 8 : 16 + i * 8]
        e = s1[8 + i * 8 : 16 + i * 8]
        mixed = e[6]
        entries.append(
            Entry(
                name=n[0:7].decode("latin1").rstrip(" "),
                directory=chr(n[7] & 0x7F),
                locked=bool(n[7] & 0x80),
                load=e[0] | e[1] << 8 | ((mixed >> 2) & 3) << 16,
                exec=e[2] | e[3] << 8 | ((mixed >> 6) & 3) << 16,
                length=e[4] | e[5] << 8 | ((mixed >> 4) & 3) << 16,
                start=e[7] | (mixed & 3) << 8,
            )
        )
    return Catalogue(
        title=title,
        cycle=s1[4],
        opt=(s1[6] >> 4) & 3,
        disc_sectors=(s1[6] & 3) << 8 | s1[7],
        entries=entries,
    )


def write_catalogue(cat: Catalogue) -> bytes:
    """The two catalogue sectors, unused space zeroed as DFS leaves it."""
    if len(cat.entries) > MAX_FILES:
        raise ValueError(f"{len(cat.entries)} files; DFS holds {MAX_FILES}")
    s0, s1 = bytearray(SECTOR), bytearray(SECTOR)
    title = cat.title.encode("latin1")
    if len(title) > 12:
        raise ValueError(f"title {cat.title!r} longer than 12 characters")
    title = title.ljust(12, b"\0")
    s0[0:8], s1[0:4] = title[0:8], title[8:12]
    s1[4] = cat.cycle
    s1[5] = len(cat.entries) * 8
    s1[6] = (cat.opt & 3) << 4 | (cat.disc_sectors >> 8) & 3
    s1[7] = cat.disc_sectors & 0xFF
    for i, e in enumerate(cat.entries):
        name = e.name.encode("latin1")
        if not 1 <= len(name) <= 7:
            raise ValueError(f"bad DFS name {e.name!r}")
        s0[8 + i * 8 : 15 + i * 8] = name.ljust(7, b" ")
        s0[15 + i * 8] = ord(e.directory) | (0x80 if e.locked else 0)
        mixed = (
            (e.start >> 8) & 3
            | ((e.load >> 16) & 3) << 2
            | ((e.length >> 16) & 3) << 4
            | ((e.exec >> 16) & 3) << 6
        )
        s1[8 + i * 8 : 16 + i * 8] = bytes(
            [e.load & 0xFF, e.load >> 8 & 0xFF, e.exec & 0xFF, e.exec >> 8 & 0xFF,
             e.length & 0xFF, e.length >> 8 & 0xFF, mixed, e.start & 0xFF]
        )
    return bytes(s0 + s1)


def file_data(image: bytes, e: Entry) -> bytes:
    return image[e.start * SECTOR : e.start * SECTOR + e.length]


def parse_inf(text: str):
    """Baron's .inf sidecar: `D.NAME load exec length`, 32-bit hex."""
    name, load, exec_, length = text.split()[:4]
    directory, _, bare = name.rpartition(".")
    return directory or "$", bare, int(load, 16), int(exec_, 16), int(length, 16)
