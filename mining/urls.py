from django.urls import path
from .views import upload_excel, purchase_pattern_analysis, generate_excel, product_consumption_analysis

urlpatterns = [
    path("upload/", upload_excel, name="upload_excel"),
    path("purchase-pattern/", purchase_pattern_analysis, name="purchase_pattern"),
    path("generate-excel/", generate_excel, name="generate_excel"),
    path("product-analysis/", product_consumption_analysis, name="product_analysis"),
]