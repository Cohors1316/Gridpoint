import socket
import sqlite3
from uuid import UUID, uuid4
from typing import overload

__all__ = ["LabelDatabase"]


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


def qr_code(x: int, y: int, id: UUID | str) -> str:
    if isinstance(id, UUID):
        id = str(id)
    return f"^FO{x},{y}^BQN,2,4^FDQAH{id}^FS"


def text(x: int, y: int, id: UUID | str) -> str:
    if isinstance(id, UUID):
        id = str(id)
    formatted_id = id.upper().split("-")
    formatted_id = f"{formatted_id[0]}-\\&{formatted_id[1]}-{formatted_id[2]}-\\&{formatted_id[3]}-\\&{formatted_id[4]}"
    return f"^FO{x},{y}^A0N,23,24^FB150,4,14,L^FD{formatted_id}^FS"


def template(id: UUID | str) -> str:
    return f"^XA^PW304{qr_code(10, 0, id)}{text(150, 10, id)}^XZ"


def double_template(id1: UUID | str, id2: UUID | str, gap: int = 500) -> str:
    return (
        "^XA^PW900"
        + qr_code(10, 0, id1)
        + text(150, 10, id1)
        + qr_code(10 + gap, 0, id2)
        + text(150 + gap, 10, id2)
        + "^XZ"
    )


class LabelDatabase:
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor
    printer_ip: str | None = None

    def __init__(
        self,
        db_name: str = "label_database.db",
        printer_ip: str | None = None
    ):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS labels (id BLOB PRIMARY KEY)")
        self.printer_ip = printer_ip

    def __contains__(self, id: UUID | set[UUID] | str | set[str]):
        return bool(self.contains(id))

    def __add__(self, other: UUID | set[UUID] | str | set[str]):
        self.save_id(other)
        return self

    def __sub__(self, other: UUID | set[UUID] | str | set[str]):
        self.delete_id(other)
        return self

    def __mul__(self, other: int) -> set[UUID]:
        return self.new_id(other)

    def new_id(self, quantity: int = 1) -> set[UUID]:
        """Generates a new UUID(s) that is not already in the database."""
        new_uuids: set[UUID] = set()
        while len(new_uuids) < quantity:
            while True:
                new_uuid = uuid4()
                if new_uuid not in self:
                    break
            new_uuids.add(new_uuid)
        return new_uuids

    def save_id(self, ids: UUID | set[UUID] | str | set[str]):
        """Saves the given IDs to the database."""
        ids = normalize(ids)
        self.cursor.executemany(
            "INSERT INTO labels VALUES (?)", [(i.bytes,) for i in ids]
        )
        self.connection.commit()

    def delete_id(self, ids: UUID | set[UUID] | str | set[str]):
        """Deletes the given ID from the database."""
        ids = normalize(ids)
        self.cursor.executemany(
            "DELETE FROM labels WHERE id = ?", [(i.bytes,) for i in ids]
        )
        self.connection.commit()

    def contains(self, ids: UUID | set[UUID] | str | set[str]) -> set[UUID]:
        """Returns whether or not the given ID is in the database."""
        found_ids: set[UUID] = set()
        ids = normalize(ids)
        # return ids of ids that are in the database
        for id in ids:
            self.cursor.execute("SELECT id FROM labels WHERE id = ?", (id.bytes,))
            if self.cursor.fetchone():
                found_ids.add(id)
        return found_ids

    @overload
    def print(self, ids: UUID | set[UUID] | str | set[str]) -> None:
        """Prints labels for the given ids"""
        ...

    @overload
    def print(self, ids: int) -> set[UUID]:
        """Creates and prints labels for the given quantity"""
        ...

    def print(self, ids: UUID | set[UUID] | str | set[str] | int) -> set[UUID] | None:
        """Prints labels with the given ID to the printer at the given IP address."""
        new_ids = self.new_id(ids) if isinstance(ids, int) else normalize(ids)
        labels = [template(id) for id in new_ids]
        if self.printer_ip is None:
            raise Exception("Printer IP not set")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.printer_ip, 9100))
            s.sendall("\n".join(labels).encode("utf-8"))
            s.close()

    def print2(self, ids: UUID | set[UUID] | str | set[str]) -> None:
        ids = normalize(ids)
        labels: list[str] = []
        while ids:
            if len(ids) == 1:
                id = ids.pop()
                labels.append(template(id))
            else:
                id1 = ids.pop()
                id2 = ids.pop()
                labels.append(double_template(id1, id2))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.printer_ip, 9100))
            s.sendall("\n".join(labels).encode("utf-8"))
            s.close()