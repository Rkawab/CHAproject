from django.db import models
from core.models import Payer, CostItem


class PrivateVariableCost(models.Model):
    """個人変動費"""

    purchase_date = models.DateField("購入日")
    amount = models.PositiveIntegerField("金額")
    cost_item = models.ForeignKey(
        CostItem, verbose_name="費目", on_delete=models.SET("その他")
    )
    description = models.CharField("名称", max_length=50)
    user = models.ForeignKey(Payer, verbose_name="使用者", on_delete=models.CASCADE)

    class Meta:
        db_table = "private_variable_cost"

    def __str__(self):
        return f"{self.purchase_date} {self.description} ({self.amount}円)"


class PrivateFixedCost(models.Model):
    """個人固定費（月次）"""

    user = models.ForeignKey(Payer, verbose_name="使用者", on_delete=models.CASCADE)
    year = models.PositiveIntegerField("年")
    month = models.PositiveSmallIntegerField("月")
    salary = models.IntegerField("給与収入", default=0, null=True, blank=True)
    deduction = models.IntegerField("差引控除額", default=0, null=True, blank=True)
    shared_cost = models.IntegerField("夫婦折半費用", default=0, null=True, blank=True)
    subscriptions = models.IntegerField("サブスク代", default=0, null=True, blank=True)
    savings = models.IntegerField("積立費用", default=20000, null=True, blank=True)

    class Meta:
        db_table = "private_fixed_cost"
        unique_together = ("user", "year", "month")
        ordering = ["-year", "-month"]
        verbose_name = "個人固定費"
        verbose_name_plural = "個人固定費"

    def __str__(self):
        return f"{self.user.name} {self.year}年{self.month}月の個人固定費"
