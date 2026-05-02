from django.db import models

class DimDate(models.Model):
    full_date = models.DateField()
    day = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    day_of_week = models.CharField(max_length=10)
    is_weekend = models.BooleanField()

class DimCustomer(models.Model):
    customer_name = models.CharField(max_length=255)

class DimProduct(models.Model):
    product_name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

class DimPayment(models.Model):
    payment_method = models.CharField(max_length=20)

class FactSales(models.Model):
    transaction_id = models.IntegerField()

    date = models.ForeignKey(DimDate, on_delete=models.CASCADE)
    customer = models.ForeignKey(DimCustomer, on_delete=models.CASCADE)
    product = models.ForeignKey(DimProduct, on_delete=models.CASCADE)
    payment = models.ForeignKey(DimPayment, on_delete=models.CASCADE)

    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)