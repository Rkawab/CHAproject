from django.db import models

class FixedCost(models.Model):
    year = models.IntegerField("年")
    month = models.IntegerField("月")
    rent = models.IntegerField("家賃", default=0, null=True, blank=True)
    water = models.IntegerField("水道代", null=True, blank=True)
    electricity = models.IntegerField("電気代", default=0, null=True, blank=True)
    gas = models.IntegerField("ガス代", default=0, null=True, blank=True)
    internet = models.IntegerField("ネット代", default=0, null=True, blank=True)
    subscriptions = models.IntegerField("サブスク代", default=0, null=True, blank=True)

    class Meta:
        db_table = 'fixed_cost'
        verbose_name = "固定費"
        verbose_name_plural = "固定費"
        unique_together = ('year', 'month')  # 年月の組み合わせは一意
        ordering = ['-year', '-month']  # 新しい年月順に並べる

    def get_adjusted_water(self):
        """水道代の調整（2か月に1回の場合）"""
        # 過去2ヶ月の水道代の平均（nullを除外）
        prev = FixedCost.objects.filter(
            year=self.year,
            month__in=[self.month, self.month - 1 if self.month > 1 else 12]
        ).exclude(water__isnull=True)

        # 前の月が別の年の場合を考慮
        if self.month == 1:
            prev_year = FixedCost.objects.filter(
                year=self.year - 1,
                month=12
            ).exclude(water__isnull=True)
            prev = list(prev) + list(prev_year)

        if prev:
            total = sum(p.water or 0 for p in prev)
            return total / len(prev)
        return 0

    def get_total_cost(self):
        """すべての固定費の合計を計算"""
        return sum(filter(None, [
            self.rent,
            self.electricity,
            self.gas,
            self.internet,
            self.subscriptions,
            self.get_adjusted_water() if self.water is None else self.water
        ]))

    def __str__(self):
        return f"{self.year}年{self.month}月の固定費"