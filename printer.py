import socket
import uuid

def label(uuid: uuid.UUID):
    return f"""
    ^XA^FO10,0^BQN,2,4,H^FDQA,{ uuid }^FS^FO150,15^A0N,25^FB150,4,10,L^FD{ uuid }^FS^XZ
    """


class Printer:
    ip: str = None
    port: int = None

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port

    def print(self, uuids: set[uuid.UUID]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            data = ''.join([label(uuid) for uuid in uuids]).encode("utf-8")
            s.sendall(data.encode())
            s.close()
