from peewee import *

db = SqliteDatabase('check-puzzles-zulip.db')

class BaseModel(Model):
    class Meta:
        database = db


class PuzzleReport(BaseModel):
    puzzle_id = IntegerField()
    report = TextField()
