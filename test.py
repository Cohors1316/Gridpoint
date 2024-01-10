from labels import Database, Zebra, Media

db = Database("test.db")
printer = Zebra("192.168.21.107")

MysteryRoll = Media(darkness=28, speed=5, margins=3, label_width=25.4, columns=3, gap=2.2)


ids = db.new_ids(20)
if db.contains(ids):
    raise Exception("ids should not be in db")

db.save_ids(ids)
if not db.contains(ids):
    raise Exception("ids should be in db")
print("ids saved:", db.contains(ids))

db.delete_ids(ids)
if db.contains(ids):
    raise Exception("ids should not be in db")
printer.print(MysteryRoll, ids)


ids = db + 20  # creates 20 new ids, not inserted into db
if ids in db:
    raise Exception("ids should not be in db")

db += ids  # inserts set of ids to db
if ids not in db:
    raise Exception("ids should be in db")
print("ids saved:", db.contains(ids))

db -= ids  # deletes set of ids from db
if ids in db:
    raise Exception("ids should not be in db")
printer(MysteryRoll, ids)

test = ids in db
