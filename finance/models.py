from django.db import models

class CostItem(models.Model):
    name = models.CharField("費目名", max_length=20)

    class Meta:
        db_table = 'item'

    def __str__(self):
        return self.name

class Payer(models.Model):  # 立替者
    name = models.CharField("立替者名", max_length=10, unique=True)

    class Meta:
        db_table = 'payer'

    def __str__(self):
        return self.name

class HouseholdAccount(models.Model):  # 家計簿
    purchase_date = models.DateField("購入日")
    amount = models.PositiveIntegerField("金額")  # 正の整数に制限
    cost_item = models.ForeignKey(CostItem, verbose_name="費目", on_delete=models.SET("その他"))
    description = models.CharField("名称", max_length=50)
    payer = models.ForeignKey(Payer, verbose_name="立替者", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'household_account'

    def __str__(self):
        return f"{self.purchase_date} {self.description} ({self.amount}円)"
