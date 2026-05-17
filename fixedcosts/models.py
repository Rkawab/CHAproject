from django.db import models
from django.db.models import Sum, Q


class Subscription(models.Model):
    name = models.CharField("内容", max_length=100)
    amount = models.PositiveIntegerField("金額（月額）")
    start_year = models.PositiveIntegerField("開始年")
    start_month = models.PositiveSmallIntegerField("開始月")
    end_year = models.PositiveIntegerField("終了年", null=True, blank=True)
    end_month = models.PositiveSmallIntegerField("終了月", null=True, blank=True)

    class Meta:
        db_table = "subscription"
        verbose_name = "サブスク"
        verbose_name_plural = "サブスク"
        ordering = ["start_year", "start_month", "name"]

    def __str__(self):
        return f"{self.name}（{self.amount}円/月）"

    def is_active(self, year: int, month: int) -> bool:
        """指定年月に有効か"""
        if (year, month) < (self.start_year, self.start_month):
            return False
        if self.end_year and self.end_month:
            if (year, month) > (self.end_year, self.end_month):
                return False
        return True

    @classmethod
    def total_for_month(cls, year: int, month: int) -> int:
        """指定年月に有効なサブスクの月額合計"""
        qs = cls.objects.filter(
            Q(start_year__lt=year) | Q(start_year=year, start_month__lte=month)
        ).filter(
            Q(end_year__isnull=True)
            | Q(end_year__gt=year)
            | Q(end_year=year, end_month__gte=month)
        )
        return qs.aggregate(total=Sum("amount"))["total"] or 0


class FixedCost(models.Model):
    year = models.IntegerField("年")
    month = models.IntegerField("月")
    rent = models.IntegerField("家賃", default=0, null=True, blank=True)
    water = models.IntegerField("水道代", null=True, blank=True)
    electricity = models.IntegerField("電気代", default=0, null=True, blank=True)
    gas = models.IntegerField("ガス代", default=0, null=True, blank=True)
    internet = models.IntegerField("ネット代", default=0, null=True, blank=True)

    class Meta:
        db_table = "fixed_cost"
        verbose_name = "固定費"
        verbose_name_plural = "固定費"
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]

    def get_adjusted_water(self):
        """水道代の調整（2か月に1回の場合）"""
        prev = FixedCost.objects.filter(
            year=self.year,
            month__in=[self.month, self.month - 1 if self.month > 1 else 12],
        ).exclude(water__isnull=True)

        if self.month == 1:
            prev_year = FixedCost.objects.filter(year=self.year - 1, month=12).exclude(
                water__isnull=True
            )
            prev = list(prev) + list(prev_year)

        if prev:
            total = sum(p.water or 0 for p in prev)
            return total / len(prev)
        return 0

    def get_total_cost(self):
        """すべての固定費の合計を計算（サブスクはSubscriptionテーブルから集計）"""
        subscription_total = Subscription.total_for_month(self.year, self.month)
        return sum(
            filter(
                None,
                [
                    self.rent,
                    self.electricity,
                    self.gas,
                    self.internet,
                    subscription_total or None,
                    self.get_adjusted_water() if self.water is None else self.water,
                ],
            )
        )

    def __str__(self):
        return f"{self.year}年{self.month}月の固定費"
