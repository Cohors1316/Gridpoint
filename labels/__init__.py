import socket
import sqlite3
from typing import overload
from uuid import UUID, uuid4

__all__ = ["Database", "Zebra", "Media", "save_and_print"]


def qr_code(id: UUID, offset: int) -> str:
    return f"^FO{0 + offset},0^BQN,2,4^FDQAH{id}^FS"


def text(id: UUID, offset: int) -> str:
    formatted_id = str(id).upper().split("-")
    formatted_id = f"{formatted_id[0]}-\\&{formatted_id[1]}-{formatted_id[2]}-\\&{formatted_id[3]}-\\&{formatted_id[4]}"
    return f"^FO{145 + offset},10^A0N,21,21^FB150,4,17,L^FD{formatted_id}^FS"


def label(id: UUID, offset: int = 0) -> str:
    return qr_code(id, offset) + text(id, offset)


def normalize(ids: UUID | set[UUID] | str | set[str]) -> set[UUID]:
    """Converts everything into a set of UUIDs"""
    if isinstance(ids, str):
        ids = {UUID(ids)}
    if isinstance(ids, UUID):
        ids = {ids}
    if isinstance(ids, set):
        # if instances are string, convert to UUID, else leave as is
        ids = {UUID(i) if isinstance(i, str) else i for i in ids}
    return ids


class Media:
    """measurements in mm"""

    darkness: int
    speed: float
    margins: float
    label_width: float
    gap: float
    columns: int

    @overload
    def __init__(self, darkness: int, speed: int, margins: float, label_width: float):
        ...

    @overload
    def __init__(
        self,
        darkness: int,
        speed: int,
        margins: float,
        label_width: float,
        columns: int,
        gap: float,
    ):
        ...

    def __init__(
        self,
        darkness: int,
        speed: int,
        margins: float = 0.0,
        label_width: float = 0.0,
        columns: int = 1,
        gap: float = 0.0,
    ):
        self.darkness = darkness
        self.speed = speed
        self.margins = margins
        self.label_width = label_width
        self.columns = columns
        self.gap = gap

    def total_width(self, printer: "Zebra") -> int:
        return int(
            (
                self.margins
                + (self.label_width * self.columns)
                + (self.gap * (self.columns - 1))
            )
            * printer.dpmm
        )

    def offset(self, printer: "Zebra", column: int = 1) -> int:
        offset = self.margins + (self.label_width + self.gap) * (column - 1)
        return int(offset * printer.dpmm)


class Zebra:
    ip_address: str
    port: int = 9100
    dpmm: int = 12  # 300 dpi
    # 203 dpi = 8 dpmm
    # 600 dpi = 24 dpmm

    def __init__(self, ip_address: str, port: int = 9100):
        self.ip_address = ip_address
        self.port = port

    def __call__(self, media: Media, ids: UUID | str | set[UUID] | set[str]):
        self.print(media, ids)

    def print(self, media: Media, ids: UUID | str | set[UUID] | set[str]):
        ids = normalize(ids)
        data: list[str] = []
        while ids:
            data.append("^XA")
            data.append(f"^PR{media.speed}")
            data.append(f"~SD{media.darkness}")
            data.append(f"^PW{media.total_width(self)}")
            for column in range(1, media.columns + 1):
                if not ids:
                    break
                data.append(label(ids.pop(), media.offset(self, column)))
            data.append("^XZ")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.ip_address, self.port))
            sock.sendall("".join(data).encode("utf-8"))
            sock.close()


class Database:
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __init__(self, db_name: str = "labels.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS labels (id BLOB PRIMARY KEY)")

    def __contains__(self, id: UUID | set[UUID] | str | set[str]):
        return bool(self.contains(id))

    def __iadd__(self, other: UUID | set[UUID] | str | set[str]):
        self.save_ids(other)
        return self

    def __isub__(self, other: UUID | set[UUID] | str | set[str]):
        self.delete_ids(other)
        return self

    def __add__(self, other: int) -> set[UUID]:
        return self.new_ids(other)

    def new_ids(self, quantity: int = 1) -> set[UUID]:
        """Generates a new UUID(s) that is not already in the database."""
        new_uuids: set[UUID] = set()
        while len(new_uuids) < quantity:
            while True:
                new_uuid = uuid4()
                if new_uuid not in self:
                    break
            new_uuids.add(new_uuid)
        return new_uuids

    def save_ids(self, ids: UUID | set[UUID] | str | set[str]):
        """Saves the given IDs to the database."""
        ids = normalize(ids)
        self.cursor.executemany(
            "INSERT INTO labels VALUES (?)", [(i.bytes,) for i in ids]
        )
        self.connection.commit()

    def delete_ids(self, ids: UUID | set[UUID] | str | set[str]):
        """Deletes the given ID from the database."""
        ids = normalize(ids)
        self.cursor.executemany(
            "DELETE FROM labels WHERE id = ?", [(i.bytes,) for i in ids]
        )
        self.connection.commit()

    def contains(self, ids: UUID | set[UUID] | str | set[str]) -> set[UUID]:
        """Returns ids already present in the database."""
        found_ids: set[UUID] = set()
        ids = normalize(ids)
        # return ids of ids that are in the database
        for id in ids:
            self.cursor.execute("SELECT id FROM labels WHERE id = ?", (id.bytes,))
            if self.cursor.fetchone():
                found_ids.add(id)
        return found_ids


@overload
def save_and_print(
    db: Database,
    printer: Zebra,
    media: Media,
    ids: UUID | str | set[UUID] | set[str],
) -> None:
    ...


@overload
def save_and_print(
    db: Database,
    printer: Zebra,
    media: Media,
    ids: int,
) -> set[UUID]:
    ...


def save_and_print(
    db: Database,
    printer: Zebra,
    media: Media,
    ids: UUID | str | set[UUID] | set[str] | int,
) -> None | set[UUID]:
    new_ids = db.new_ids(ids) if isinstance(ids, int) else normalize(ids)
    db.save_ids(new_ids)
    printer.print(media, new_ids)
    if isinstance(ids, int):
        return new_ids
