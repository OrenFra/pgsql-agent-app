from tortoise import fields, models


class DirRecord(models.Model):
    id = fields.IntField(pk=True)
    entity = fields.ForeignKeyField("models.Entity", related_name="dir_records", null=False)
    path = fields.CharField(max_length=255, null=False)
    raw_path = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "dir_records"
        unique_together = [("entity_id", "id"), ("entity_id", "path")]
