import socket
import sqlite3
from typing import overload, Literal, Self
from uuid import UUID, uuid4
from datetime import datetime


__all__ = ["Database", "Zebra", "Media", "save_and_print"]


def qr_code(id: UUID, offset: int) -> str:
    return f"^FO{0 + offset},0^BQN,2,4^FDQAH{id}^FS"


def text(id: UUID, offset: int) -> str:
    fmt_id = str(id).upper().split("-")
    fmt_id = f"{fmt_id[0]}-\\&{fmt_id[1]}-{fmt_id[2]}-\\&{fmt_id[3]}-\\&{fmt_id[4]}"
    return f"^FO{145 + offset},10^A0N,21,21^FB150,4,17,L^FD{fmt_id}^FS"


def label(id: UUID, offset: int = 0) -> str:
    return qr_code(id, offset) + text(id, offset)


def normalize(ids: UUID | str | set[UUID] | set[str] | bytes | set[bytes]) -> set[UUID]:
    """Converts everything into a set of UUIDs"""
    if isinstance(ids, str):
        return {UUID(ids)}
    elif isinstance(ids, UUID):
        return {ids}
    elif isinstance(ids, bytes):
        return {UUID(bytes=ids)}
    else:
        values: set[UUID] = set()
        for i in ids:
            if isinstance(i, UUID):
                values.add(i)
            elif isinstance(i, str):
                values.add(UUID(i))
            elif isinstance(i, bytes):
                values.add(UUID(bytes=i))
        return values


def placeholder(ids: set[UUID]) -> str:
    """Returns a placeholder string for the given ids."""
    return ", ".join(["?" for _ in ids])


def set_date(
    db: "Database",
    ids: UUID | str | set[UUID] | set[str],
    date: datetime,
    field: Literal["test_date", "ship_date"],
):
    ids = normalize(ids)
    if ids not in db:
        raise db.UUIDNotInDatabase("ids not in database")
    db.cursor.executemany(
        f"UPDATE labels SET {field} = ? WHERE id = ?",
        tuple((date.replace(microsecond=0), id.bytes) for id in ids),
    )
    db.connection.commit()


def get_date(
    db: "Database",
    ids: UUID | str | set[UUID] | set[str],
    field: Literal["test_date", "ship_date"],
) -> list[tuple[UUID, datetime | None]] | datetime | None:
    ids_set = normalize(ids)
    if ids not in db:
        raise db.UUIDNotInDatabase("ids not in database")
    db.cursor.execute(
        f"SELECT id, {field} FROM labels WHERE id IN ({placeholder(ids_set)})",
        tuple(i.bytes for i in ids_set),
    )
    found_ids = db.cursor.fetchall()
    if isinstance(ids, (UUID, str)):
        if not found_ids:
            return None
        value = found_ids.pop()[1]
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S") if value else None
    return [
        (
            UUID(bytes=i[0]),
            datetime.strptime(i[1], "%Y-%m-%d %H:%M:%S") if i[1] else None,
        )
        for i in found_ids
    ]


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
    dpmm: int = 12  # 300 dpi | 203 dpi = 8 dpmm | 600 dpi = 24 dpmm

    def __init__(self, ip_address: str, port: int = 9100):
        self.ip_address = ip_address
        self.port = port

    def __call__(self, media: Media, ids: UUID | str | set[UUID] | set[str]):
        self.print(media, ids)

    def print(self, media: Media, ids: UUID | str | set[UUID] | set[str]):
        ids = normalize(ids)
        if not ids:
            return
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

    class DuplicateUUID(Exception):
        pass

    class UUIDNotInDatabase(Exception):
        pass

    def __init__(self, db_name: str = "labels.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS labels (id BLOB PRIMARY KEY, test_date TEXT, ship_date TEXT)"
        )

    def __len__(self) -> int:  # len(self)
        self.cursor.execute("SELECT COUNT(*) FROM labels")
        return int(self.cursor.fetchone()[0])

    def __contains__(self, id: UUID | set[UUID] | str | set[str]) -> bool:  # x in self
        return bool(self.contains(id))

    def __iadd__(self, other: UUID | set[UUID] | str | set[str]) -> Self:  # self += y
        self.save_ids(other)
        return self

    def __isub__(
        self, other: UUID | set[UUID] | str | set[str] | Self
    ) -> Self:  # self -= y
        if isinstance(other, Database):
            self.cursor.execute("DELETE FROM labels")
            self.connection.commit()
            return self
        self.delete_ids(other)
        return self

    def __rsub__(
        self, other: UUID | set[UUID] | str | set[str]
    ) -> set[UUID]:  # y = x - self
        """Returns a set of all uuids in ids that are not in the database."""
        ids = normalize(other)
        self.cursor.execute(
            f"SELECT id FROM labels WHERE id IN ({placeholder(ids)})",
            tuple(i.bytes for i in ids),
        )
        found_ids = {UUID(bytes=i[0]) for i in self.cursor.fetchall()}
        return ids.difference(found_ids)

    def __add__(self, other: int) -> set[UUID]:  # y = self + x
        return self.new_ids(other)

    def __iter__(self):  # iter(self), for i in self, set(self), list(self)
        self.cursor.execute("SELECT id FROM labels")
        ids = {UUID(bytes=i[0]) for i in self.cursor.fetchall()}
        return iter(ids)

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
        if ids in self:
            raise self.DuplicateUUID("ids already in database")
        self.cursor.executemany(
            "INSERT INTO labels VALUES (?, ?, ?)",
            tuple((i.bytes, None, None) for i in ids),
        )
        self.connection.commit()

    def delete_ids(self, ids: UUID | set[UUID] | str | set[str]):
        """Deletes the given ID from the database."""
        ids = normalize(ids)
        self.cursor.execute(
            f"DELETE FROM labels WHERE id IN ({placeholder(ids)})",
            tuple(i.bytes for i in ids),
        )
        self.connection.commit()

    def contains(self, ids: UUID | set[UUID] | str | set[str]) -> bool:
        """Returns True if all ids are in the database."""
        ids_set = normalize(ids)
        self.cursor.execute(
            f"SELECT id FROM labels WHERE id IN ({placeholder(ids_set)})",
            tuple(i.bytes for i in ids_set),
        )
        return len(ids_set) == len({UUID(bytes=i[0]) for i in self.cursor.fetchall()})

    def set_test_date(
        self, ids: UUID | set[UUID] | str | set[str], date: datetime = datetime.now()
    ):
        """Sets the test date for the given ID. Returns True if the date was already set."""
        set_date(self, ids, date, "test_date")

    def set_ship_date(
        self, ids: UUID | set[UUID] | str | set[str], date: datetime = datetime.now()
    ):
        """Sets the ship date for the given ID. Returns True if the date was already set."""
        set_date(self, ids, date, "ship_date")

    @overload
    def ship_date(self, ids: UUID | str) -> datetime | None:
        ...

    @overload
    def ship_date(
        self, ids: set[UUID] | set[str]
    ) -> list[tuple[UUID, datetime | None]]:
        ...

    def ship_date(
        self, ids: UUID | str | set[UUID] | set[str]
    ) -> list[tuple[UUID, datetime | None]] | datetime | None:
        """Returns ids that have been shipped."""
        return get_date(self, ids, "ship_date")

    @overload
    def test_date(self, ids: UUID | str) -> datetime | None:
        ...

    @overload
    def test_date(
        self, ids: set[UUID] | set[str]
    ) -> list[tuple[UUID, datetime | None]]:
        ...

    def test_date(
        self, ids: UUID | set[UUID] | str | set[str]
    ) -> list[tuple[UUID, datetime | None]] | datetime | None:
        """Returns ids that have been tested."""
        return get_date(self, ids, "test_date")


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
