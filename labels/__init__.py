import socket
import sqlite3
import uuid
from typing import Set

__all__ = ["init_database", "new", "print", "print_batch"]


def label_template(uuid: uuid.UUID) -> str:
    """returns zpl code for a label with the given uuid"""
    return f"""
    ^XA^FO10,0^BQN,2,4,H^FDQA,{ uuid }^FS^FO150,15^A0N,25^FB150,4,10,L^FD{ uuid }^FS^XZ
    """


def label_exists(label: uuid.UUID | str) -> bool:
    """checks to see if a uuid already exists in the database"""
    if isinstance(label, str):
        label = uuid.UUID(label)
    connection = sqlite3.connect("label_database.db")
    cursor = connection.cursor()
    result = cursor.execute(
        "SELECT * FROM labels WHERE id = ?", (label.bytes,)
    ).fetchone()
    connection.close()
    return result is not None


def init_database():
    """creates the label database and table if it doesn't exist"""
    connection = sqlite3.connect("label_database.db")
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS labels (id BLOB PRIMARY KEY)")
    connection.commit()
    connection.close()


def print(ip: str, label: uuid.UUID | str):
    """prints a label for the given uuid"""
    if isinstance(label, str):
        label = uuid.UUID(label)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, 9100))
        s.sendall(label_template(label).encode("utf-8"))
        s.close()


def print_batch(ip: str, quantity: int) -> Set[uuid.UUID]:
    """prints a batch of labels"""
    new_uuids: set[uuid.UUID] = set()
    while len(new_uuids) < quantity:
        new_uuids.add(new())
    labels = [label_template(label) for label in new_uuids]
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, 9100))
        s.sendall("\n".join(labels).encode("utf-8"))
        s.close()
    return new_uuids


def new() -> uuid.UUID:
    """creates a new uuid in the database"""
    connection = sqlite3.connect("label_database.db")
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS labels (id BLOB PRIMARY KEY)")
    connection.commit()
    while True:
        new_uuid = uuid.uuid4()
        if not label_exists(new_uuid):
            break
    cursor.execute("INSERT INTO labels VALUES (?)", (new_uuid.bytes,))
    connection.close()
    return new_uuid
