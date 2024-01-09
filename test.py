from labels import LabelDatabase

db = LabelDatabase("test.db", "192.168.21.107")

ids = db.new_id(13)
if db.contains(ids):
    raise Exception("ids should not be in db")

db.save_id(ids)
if not db.contains(ids):
    raise Exception("ids should be in db")

db.print2(ids)

db.delete_id(ids)
if db.contains(ids):
    raise Exception("ids should not be in db")