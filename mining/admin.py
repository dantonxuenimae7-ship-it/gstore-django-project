from django.contrib import admin
from .models import *

admin.site.register(DimDate)
admin.site.register(DimCustomer)
admin.site.register(DimProduct)
admin.site.register(DimPayment)
admin.site.register(FactSales)