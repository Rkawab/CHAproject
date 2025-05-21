from django.db import models

class CostItem(models.Model):
    name = models.CharField("費目名", max_length=20)

    class Meta:
        db_table = 'item'
    def __str__(self):
        return self.name

class Payer(models.Model):
    name = models.CharField("立替者名", max_length=10, unique=True)

    class Meta:
        db_table = 'payer'

    def __str__(self):
        return self.name
