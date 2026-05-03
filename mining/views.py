# =========================
# IMPORTS
# =========================
import random
import io
import base64

import pandas as pd
import matplotlib.pyplot as plt

from faker import Faker
from django.shortcuts import render
from django.http import HttpResponse

from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

from .models import (
    DimDate,
    DimCustomer,
    DimProduct,
    DimPayment,
    FactSales
)


# =========================
# GRAPH HELPER
# =========================
def get_graph():
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    return base64.b64encode(image_png).decode('utf-8')


# =========================
# ETL UPLOAD FUNCTION
# =========================
def upload_excel(request):

    if request.method == "POST":
        file = request.FILES["excel_file"]

        # EXTRACT
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.lower()

        print(df.columns)

        # CLEANING
        df.dropna(inplace=True)
        df.drop_duplicates(inplace=True)

        # DATE COLUMN DETECTION
        date_column = next(
            (col for col in df.columns
             if col in ["date", "transaction_date", "sales_date"]),
            None
        )

        if not date_column:
            return render(request, "upload.html", {
                "message": "❌ No valid date column found in Excel file"
            })

        df["date"] = pd.to_datetime(df[date_column], errors="coerce")
        df.dropna(subset=["date"], inplace=True)

        # NUMERIC CLEANING
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
        df["total_amount"] = df["quantity"] * df["price"]

        # TEXT CLEANING
        df["customer_name"] = df["customer_name"].str.title().str.strip()
        df["product_name"] = df["product_name"].str.title().str.strip()

        # LOAD TO STAR SCHEMA
        for _, row in df.iterrows():

            date_obj, _ = DimDate.objects.get_or_create(
                full_date=row["date"].date(),
                defaults={
                    "day": row["date"].day,
                    "month": row["date"].month,
                    "year": row["date"].year,
                    "day_of_week": row["date"].strftime("%A"),
                    "is_weekend": row["date"].weekday() >= 5
                }
            )

            customer_obj, _ = DimCustomer.objects.get_or_create(
                customer_name=row["customer_name"]
            )

            product_obj, _ = DimProduct.objects.get_or_create(
                product_name=row["product_name"],
                defaults={
                    "category": row.get("category", "Unknown"),
                    "price": row["price"]
                }
            )

            payment_obj, _ = DimPayment.objects.get_or_create(
                payment_method=row.get("payment_method", "Cash")
            )

            FactSales.objects.create(
                transaction_id=row.get("transaction_id", 0),
                date=date_obj,
                customer=customer_obj,
                product=product_obj,
                payment=payment_obj,
                quantity=int(row["quantity"]),
                total_amount=float(row["total_amount"])
            )

        return render(request, "upload.html", {
            "message": "✅ ETL Upload Successful! Data loaded into warehouse."
        })

    return render(request, "upload.html")


# =========================
# GENERATE SAMPLE EXCEL
# =========================
def generate_excel(request):

    fake = Faker()
    NUM_ROWS = 1000

    products = [
        {"name": "Rice 1kg", "price": 60, "category": "Food"},
        {"name": "Instant Noodles", "price": 12, "category": "Food"},
        {"name": "Softdrinks", "price": 20, "category": "Beverage"},
        {"name": "Bread", "price": 15, "category": "Food"},
        {"name": "Coffee", "price": 10, "category": "Beverage"},
    ]

    data = []

    for i in range(NUM_ROWS):
        product = random.choice(products)
        qty = random.randint(1, 5)

        data.append({
            "transaction_id": i + 1,
            "date": fake.date_between(start_date="-1y", end_date="today"),
            "customer_name": fake.name(),
            "product_name": product["name"],
            "category": product["category"],
            "price": product["price"],
            "quantity": qty,
            "total_amount": qty * product["price"],
        })

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    response["Content-Disposition"] = 'attachment; filename="grocery_sales_1000.xlsx"'

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    return response


# =========================
# PRODUCT CONSUMPTION ANALYSIS
# =========================
def product_consumption_analysis(request):
    return render(request, 'analysis.html')

    data = FactSales.objects.all().values(
        "date",
        "quantity",
        "product__product_name"
    )

    df = pd.DataFrame(data)

    if df.empty:
        return render(request, "analysis.html", {
            "message": "No data available"
        })

    df["date"] = pd.to_datetime(df["date"])

    # DAILY
    daily = df.groupby(df["date"].dt.date)["quantity"].sum()

    plt.figure()
    daily.plot()
    plt.title("Daily Product Consumption")
    plt.xlabel("Date")
    plt.ylabel("Quantity")
    daily_graph = get_graph()
    plt.close()

    # WEEKLY
    weekly = df.groupby(df["date"].dt.isocalendar().week)["quantity"].sum()

    plt.figure()
    weekly.plot()
    plt.title("Weekly Product Consumption")
    plt.xlabel("Week")
    plt.ylabel("Quantity")
    weekly_graph = get_graph()
    plt.close()

    # MONTHLY
    monthly = df.groupby(df["date"].dt.month)["quantity"].sum()

    plt.figure()
    monthly.plot()
    plt.title("Monthly Product Consumption")
    plt.xlabel("Month")
    plt.ylabel("Quantity")
    monthly_graph = get_graph()
    plt.close()

    return render(request, "analysis.html", {
        "daily_graph": daily_graph,
        "weekly_graph": weekly_graph,
        "monthly_graph": monthly_graph,
    })


# =========================
# PURCHASE PATTERN ANALYSIS (APRIORI)
# =========================
def purchase_pattern_analysis(request):

    data = FactSales.objects.all().values(
        "transaction_id",
        "product__product_name"
    )

    df = pd.DataFrame(data)

    if df.empty:
        return render(request, "purchase_pattern.html", {
            "message": "No data available for analysis"
        })

    # BASKET CREATION
    baskets = df.groupby("transaction_id")["product__product_name"].apply(list)

    # ONE-HOT ENCODING
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)

    # APRIORI
    freq_items = apriori(basket_df, min_support=0.02, use_colnames=True)

    rules = association_rules(freq_items, metric="confidence", min_threshold=0.3)

    # CLEAN OUTPUT
    rules_data = rules[[
        "antecedents",
        "consequents",
        "support",
        "confidence",
        "lift"
    ]].copy()

    rules_data["antecedents"] = rules_data["antecedents"].apply(lambda x: ", ".join(list(x)))
    rules_data["consequents"] = rules_data["consequents"].apply(lambda x: ", ".join(list(x)))

    rules_data = rules_data.sort_values(by="lift", ascending=False).head(20)

    return render(request, "purchase_pattern.html", {
        "rules": rules_data.to_dict(orient="records")
    })