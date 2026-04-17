# 🚀 FINAL PRODUCTION GST BILLING SOFTWARE

import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="GST Billing Software", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("invoice.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS invoices(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT,
    total REAL,
    date TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS customers(
    name TEXT,
    phone TEXT,
    gst TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS products(
    name TEXT,
    price REAL
)""")
conn.commit()

# ---------------- SIDEBAR ----------------
menu = st.sidebar.radio("Navigation", [
    "Create Invoice",
    "Invoice History",
    "Customer Master",
    "Product Master",
    "Dashboard"
])

# ---------------- COMMON ----------------
def calculate(items, transport):
    subtotal = sum(q*p for _,q,p in items)
    gst = subtotal * 0.18
    total = subtotal + gst + transport
    return subtotal, gst, total

# ---------------- CREATE INVOICE ----------------
if menu == "Create Invoice":
    st.title("Create Invoice")

    customer = st.text_input("Customer Name")
    phone = st.text_input("Phone")
    gstin = st.text_input("GSTIN")

    invoice_date = st.date_input("Date", date.today())
    formatted_date = invoice_date.strftime("%d-%m-%Y")

    items = []
    rows = st.number_input("No. of Items", 1, 10, 1)

    for i in range(int(rows)):
        col1, col2, col3 = st.columns(3)
        name = col1.text_input(f"Item {i+1}")
        qty = col2.number_input(f"Qty {i+1}", 1, key=f"q{i}")
        price = col3.number_input(f"Price {i+1}", key=f"p{i}")
        items.append((name, qty, price))

    transport = st.number_input("Transport", 0.0)

    subtotal, gst, total = calculate(items, transport)

    st.subheader("Summary")
    st.write("Subtotal:", subtotal)
    st.write("GST (18%):", gst)
    st.write("Total:", total)

    if st.button("Save Invoice"):
        c.execute("INSERT INTO invoices(customer,total,date) VALUES(?,?,?)",
                  (customer, total, formatted_date))
        conn.commit()
        st.success("Invoice Saved")

    if st.button("Download PDF"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        if os.path.exists("logo.png"):
            elements.append(Image("logo.png", 80, 80))

        elements.append(Paragraph(f"<b>Invoice</b>", styles['Title']))
        elements.append(Paragraph(f"Customer: {customer}", styles['Normal']))
        elements.append(Paragraph(f"Date: {formatted_date}", styles['Normal']))
        elements.append(Spacer(1, 20))

        data = [["Item", "Qty", "Price", "Total"]]
        for name, qty, price in items:
            data.append([name, qty, price, qty*price])

        table = Table(data)
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black)
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph(f"Total: {total}", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)

        st.download_button("Download", buffer, file_name="invoice.pdf")

# ---------------- HISTORY ----------------
elif menu == "Invoice History":
    st.title("Invoice History")
    df = pd.read_sql("SELECT * FROM invoices", conn)
    st.dataframe(df)

# ---------------- CUSTOMER MASTER ----------------
elif menu == "Customer Master":
    st.title("Customer Master")

    name = st.text_input("Name")
    phone = st.text_input("Phone")
    gst = st.text_input("GST")

    if st.button("Add Customer"):
        c.execute("INSERT INTO customers VALUES(?,?,?)", (name, phone, gst))
        conn.commit()
        st.success("Customer Added")

    df = pd.read_sql("SELECT * FROM customers", conn)
    st.dataframe(df)

# ---------------- PRODUCT MASTER ----------------
elif menu == "Product Master":
    st.title("Product Master")

    name = st.text_input("Product Name")
    price = st.number_input("Price")

    if st.button("Add Product"):
        c.execute("INSERT INTO products VALUES(?,?)", (name, price))
        conn.commit()
        st.success("Product Added")

    df = pd.read_sql("SELECT * FROM products", conn)
    st.dataframe(df)

# ---------------- DASHBOARD ----------------
elif menu == "Dashboard":
    st.title("Dashboard")

    df = pd.read_sql("SELECT * FROM invoices", conn)

    st.metric("Total Invoices", len(df))
    st.metric("Total Revenue", df['total'].sum() if not df.empty else 0)
