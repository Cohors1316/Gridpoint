from labels import Database, Zebra, SingleLabelRoll, DoubleLabelRoll

db = Database("test.db", "192.168.21.107")
printer = Zebra("192.168.21.107")

ids = db.new_ids(13)
if db.contains(ids):
    raise Exception("ids should not be in db")

db.save_ids(ids)
if not db.contains(ids):
    raise Exception("ids should be in db")
print("ids saved:", db.contains(ids))

db.delete_ids(ids)
if db.contains(ids):
    raise Exception("ids should not be in db")
printer.print(DoubleLabelRoll, ids)

ids = db * 3
if ids in db:
    raise Exception("ids should not be in db")

db += ids
if ids not in db:
    raise Exception("ids should be in db")
print("ids saved:", db.contains(ids))


db -= ids
if ids in db:
    raise Exception("ids should not be in db")
printer(DoubleLabelRoll, ids)