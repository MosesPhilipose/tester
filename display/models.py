# H:\New folder (2)\display\models.py
from django.db import models

class ReportTime(models.Model):
    time = models.CharField(max_length=20)  # e.g., "05:20 AM"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.time

class ReportDate(models.Model):
    date = models.CharField(max_length=50)  # e.g., "March 25, 2025"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.date

class TickerData(models.Model):
    symbol = models.CharField(max_length=50)
    opening_scenario = models.CharField(max_length=50)
    trend_observed = models.CharField(max_length=50)
    upward_close = models.FloatField()
    downward_close = models.FloatField()
    flat_close = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.symbol
