from labels import Database, Media, Zebra, save_and_print
from datetime import datetime


db = Database("test.db")
printer = Zebra("192.168.21.107")

MysteryRoll = Media(
    darkness=28, speed=5, margins=3, label_width=25.4, columns=3, gap=2.2
)
"""
darkness is a global printer setting, small changes tend to make a big difference

speed is inches per second, whole numbers only

margins is in mm, is the outermost webbing on the roll

label_width is in mm and is the width of individual labels

columns is the number of labels across the roll

gap is the distance between labels in mm

columns and gap are not required if there is only one column

label height is not required as the printer calculates it when labels are changed

annoyingly, different label types required vastly different darkness and speed settings
"""

db -= db

ids = db.new_ids(20)
if db.contains(ids):
    raise Exception("ids should not be in db")
if len(ids) != 20:
    raise Exception("ids should have 20 ids")
db.save_ids(ids)
if not db.contains(ids):
    raise Exception("ids should be in db")
db.delete_ids(ids)
if db.contains(ids):
    raise Exception("ids should not be in db")

# Testing dunder methods
ids = db + 20  # creates 20 new ids, not inserted into db
if ids in db:
    raise Exception("ids should not be in db")

db += ids  # inserts set of ids to db
if ids not in db:
    raise Exception("ids should be in db")

new_ids = db + 20
if new_ids in db:
    raise Exception("ids should not be in db")

combined_ids = ids | new_ids
if combined_ids in db:  # `in` will return false if any id is not in db
    raise Exception("some ids should not be in db")

unsaved_ids = combined_ids - db  # ids in combined_ids that are not in db
if unsaved_ids in db:
    raise Exception("ids should not be in db")

if not new_ids == unsaved_ids:
    raise Exception("ids should be the same")

db += unsaved_ids
if unsaved_ids not in db:
    raise Exception("ids should be in db")

if len(db) != 40:  # len should return total number of ids in db
    raise Exception("db should have 40 ids")

db -= unsaved_ids  # deletes set of ids from db
if unsaved_ids in db:
    raise Exception("ids should not be in db")

if len(db) != 20:
    raise Exception("db should have 20 ids")

db -= db
if len(db) != 0:
    raise Exception("db should have 0 ids")

# Testing test_date methods
ids = db + 20
single_id = ids.pop()
second_id = ids.pop()

if single_id in db:
    raise Exception("ids should not be in db")

db += single_id
test_date = db.test_date(single_id)
if test_date is not None:
    raise Exception("test_date should be None")

db.set_test_date(single_id)
test_date = db.test_date(single_id)
if test_date is None:
    raise Exception("test_date should not be None")

db += second_id
db.set_test_date(second_id, datetime(2021, 1, 1))
test_date = db.test_date(second_id)
if test_date is None:
    raise Exception("test_date should not be None")

if test_date != datetime(2021, 1, 1):
    raise Exception("test_date should be 2021-01-01")

db += ids
test_dates = db.test_date(ids)
if test_dates is None:
    raise Exception("test_dates should not be None")

if len(test_dates) != len(ids):
    raise Exception("test_dates should have same length as ids")

for date in test_dates:
    if date is None:
        raise Exception("test_dates should not contain None")

# Testing ship_date methods
ship_date = db.ship_date(single_id)
if ship_date is not None:
    raise Exception("ship_date should be None")

db.set_ship_date(single_id)
ship_date = db.ship_date(single_id)
if ship_date is None:
    raise Exception("ship_date should not be None")

db.set_ship_date(second_id, datetime(2021, 1, 1))
ship_date = db.ship_date(second_id)
if ship_date is None:
    raise Exception("ship_date should not be None")

if ship_date != datetime(2021, 1, 1):
    raise Exception("ship_date should be 2021-01-01")

ship_dates = db.ship_date(ids)
if ship_dates is None:
    raise Exception("ship_dates should not be None")

if len(ship_dates) != len(ids):
    raise Exception("ship_dates should have same length as ids")

for date in ship_dates:
    if date is None:
        raise Exception("ship_dates should not contain None")

# testing print methods
# saves ids
printed_ids = save_and_print(db, printer, MysteryRoll, 3)
db -= printed_ids
save_and_print(db, printer, MysteryRoll, printed_ids)  # reusing ids
db -= printed_ids

# does not save ids
printer.print(MysteryRoll, printed_ids)
printer(MysteryRoll, printed_ids)
printer.print(MysteryRoll, printed_ids.pop())

# testing error handling
test_id = db + 1
db += test_id
try:
    db += test_id
    raise Exception("should have raised error")
except Database.DuplicateUUID:
    pass
except Exception:
    raise Exception("should have raised Database.DuplicateUUID")

test_id = db + 1
try:
    db.set_test_date(test_id)
    raise Exception("should have raised error")
except Database.UUIDNotInDatabase:
    pass
except Exception:
    raise Exception("should have raised Database.UUIDNotInDatabase")

try:
    db.set_ship_date(test_id)
    raise Exception("should have raised error")
except Database.UUIDNotInDatabase:
    pass
except Exception:
    raise Exception("should have raised Database.UUIDNotInDatabase")

db -= db
print("All tests passed!")
exit()
# cheat sheet

# get number of new uuids
ids = db + 10
ids = db.new_ids(10)


# save uuids to db
db += ids
db.save_ids(ids)


# delete uuids from db
db -= ids
db.delete_ids(ids)


# uuids not in db
not_saved = ids - db


# get total number of uuids in db
len(db)


# iterate over uuids in db
for uuid in db: pass
set(db)
list(db)
iter(db)


# compare uuids to db
if ids in db: pass
db.contains(ids)


# clear db
db -= db


# print labels from ids
printer.print(MysteryRoll, ids)
printer(MysteryRoll, ids)


# save and print labels from ids
save_and_print(db, printer, MysteryRoll, ids)


# create ids, save, and print labels
printed_ids = save_and_print(db, printer, MysteryRoll, 10)