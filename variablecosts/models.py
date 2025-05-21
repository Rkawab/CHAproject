from django.db import models
from core.models import Payer, CostItem

class VariableCost(models.Model):  # 家計簿
    purchase_date = models.DateField("購入日")
    amount = models.PositiveIntegerField("金額")  # 正の整数に制限
    cost_item = models.ForeignKey(CostItem, verbose_name="費目", on_delete=models.SET("その他"))
    description = models.CharField("名称", max_length=50)
    payer = models.ForeignKey(Payer, verbose_name="立替者", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'variable_cost'

    def __str__(self):
        return f"{self.purchase_date} {self.description} ({self.amount}円)"
