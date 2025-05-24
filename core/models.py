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

class Budget(models.Model):
    CATEGORY_CHOICES = [
        ('fixed', '固定費'),
        ('variable', '変動費'),
    ]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, unique=True)
    amount = models.PositiveIntegerField(verbose_name="予算額（円）")

    def __str__(self):
        return f"{self.get_category_display()}：{self.amount}円"