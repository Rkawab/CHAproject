from django.db import models
from django.db.models import Q, Sum
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


class PrivateAnnualInfo(models.Model):
    """個人年間情報"""

    user = models.ForeignKey(Payer, verbose_name="使用者", on_delete=models.CASCADE)
    year = models.PositiveIntegerField("年")
    summer_bonus = models.IntegerField("夏季賞与", default=0, null=True, blank=True)
    winter_bonus = models.IntegerField("冬季賞与", default=0, null=True, blank=True)

    class Meta:
        db_table = "private_annual_info"
        unique_together = ("user", "year")
        ordering = ["-year"]
        verbose_name = "個人年間情報"
        verbose_name_plural = "個人年間情報"

    def __str__(self):
        return f"{self.user.name} {self.year}年の個人年間情報"


class PrivateSubscription(models.Model):
    """個人用サブスク"""

    user = models.ForeignKey(Payer, verbose_name="使用者", on_delete=models.CASCADE)
    name = models.CharField("内容", max_length=100)
    amount = models.PositiveIntegerField("金額（月額）")
    start_year = models.PositiveIntegerField("開始年")
    start_month = models.PositiveSmallIntegerField("開始月")
    end_year = models.PositiveIntegerField("終了年", null=True, blank=True)
    end_month = models.PositiveSmallIntegerField("終了月", null=True, blank=True)

    class Meta:
        db_table = "private_subscription"
        verbose_name = "個人用サブスク"
        verbose_name_plural = "個人用サブスク"
        ordering = ["user__name", "start_year", "start_month", "name"]

    def __str__(self):
        return f"{self.user.name} {self.name}（{self.amount}円/月）"

    def is_active(self, year: int, month: int) -> bool:
        """指定年月に有効か"""
        if (year, month) < (self.start_year, self.start_month):
            return False
        if self.end_year and self.end_month:
            if (year, month) > (self.end_year, self.end_month):
                return False
        return True

    @classmethod
    def total_for_month(cls, user: Payer, year: int, month: int) -> int:
        """指定使用者・年月に有効なサブスクの月額合計"""
        qs = cls.objects.filter(user=user).filter(
            Q(start_year__lt=year) | Q(start_year=year, start_month__lte=month)
        ).filter(
            Q(end_year__isnull=True)
            | Q(end_year__gt=year)
            | Q(end_year=year, end_month__gte=month)
        )
        return qs.aggregate(total=Sum("amount"))["total"] or 0
