from django.db import models


class CostItem(models.Model):
    name = models.CharField("費目名", max_length=20)

    class Meta:
        db_table = "item"
        # カスタム順序：「その他」を最後に、それ以外はID順
        ordering = ["id"]

    @classmethod
    def get_ordered_items(cls):
        """「その他」を最後に表示する順序でCostItemを取得"""
        all_items = cls.objects.all()
        other_item = None
        ordered_items = []

        for item in all_items:
            if item.name == "その他":
                other_item = item
            else:
                ordered_items.append(item)

        # 「その他」を最後に追加
        if other_item:
            ordered_items.append(other_item)

        return ordered_items

    def __str__(self):
        return self.name


class Payer(models.Model):
    name = models.CharField("立替者名", max_length=10, unique=True)

    class Meta:
        db_table = "payer"

    def __str__(self):
        return self.name


class Budget(models.Model):
    CATEGORY_CHOICES = [
        ("fixed", "固定費"),
        ("variable", "変動費"),
    ]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, unique=True)
    amount = models.PositiveIntegerField(verbose_name="予算額（円）")

    def __str__(self):
        return f"{self.get_category_display()}：{self.amount}円"


class CreditCard(models.Model):
    """クレジットカード情報"""

    name = models.CharField("クレカ名", max_length=50)
    owner = models.ForeignKey(
        "core.Payer",
        verbose_name="所有者",
        on_delete=models.PROTECT,
        related_name="credit_cards",
    )
    note = models.CharField("メモ", max_length=100, blank=True, default="")

    class Meta:
        db_table = "credit_card"
        unique_together = ("name", "owner")
        ordering = ["owner__name", "name"]

    def __str__(self):
        return f"{self.name} - {self.owner.name}"


class PaymentItem(models.Model):
    """固定費支払いの控え（費用名 → クレカ）"""

    name = models.CharField("費用名", max_length=50, unique=True)
    card = models.ForeignKey(
        CreditCard,
        verbose_name="クレカ",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_items",
    )
    memo = models.CharField("メモ", max_length=100, blank=True, default="")
    sort_order = models.PositiveIntegerField("表示順", default=0)

    class Meta:
        db_table = "payment_item"
        ordering = ["sort_order", "id"]

    def __str__(self):
        if self.card_id:
            return f"{self.name} -> {self.card}"
        return f"{self.name} (未設定)"
