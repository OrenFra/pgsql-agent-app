from tortoise import fields, models


class Entity(models.Model):
    id = fields.IntField(pk=True)
    host_name = fields.CharField(max_length=255, null=False)
    project = fields.ForeignKeyField(
        "models.Project", related_name="entities", null=False
    )

    class Meta:
        table = "entities"
        unique_together = [("host_name", "project_id")]
