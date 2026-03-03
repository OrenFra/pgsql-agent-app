from tortoise import fields, models


class Project(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, unique=True, null=False)

    class Meta:
        table = "projects"
