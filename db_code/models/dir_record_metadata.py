from tortoise import fields, models
import datetime
from tortoise.fields import Field


# costume field for timestamp without time zone
# class NativeDatetimeField(Field[datetime.datetime], datetime.datetime):
#     SQL_TYPE = "TIMESTAMP WITHOUT TIME ZONE"


class DirRecordMetadata(models.Model):
    id = fields.IntField(pk=True)
    entity = fields.ForeignKeyField("models.Entity", related_name="dir_records_metadata", null=False)
    dir_record = fields.ForeignKeyField("models.DirRecord", related_name="dir_records_metadata", null=False)
    creation_time = fields.DatetimeField(null=True)
    last_updated = fields.DatetimeField(null=True)
    base_name = fields.CharField(null=False, max_length=255)
    file_extension = fields.CharField(null=False, max_length=255)

    class Meta:
        table = "dir_records_metadata"
        unique_together = [("entity_id", "id")]
