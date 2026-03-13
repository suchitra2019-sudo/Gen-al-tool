import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

st.set_page_config(page_title="Professional GST Billing", layout="wide")

# ---------------- DATABASE ----------------

conn = sqlite3.connect("billing.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_no INTEGER,
customer TEXT,
date TEXT,
total REAL)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
contact TEXT,
gstin TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
price REAL)
""")

conn.commit()

# ---------------- PDF GENERATOR ----------------

def generate_pdf(invoice_no, customer, date, items, total):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("<b>GST TAX INVOICE</b>", styles['Title']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Invoice No : {invoice_no}", styles['Normal']))
    elements.append(Paragraph(f"Customer : {customer}", styles['Normal']))
    elements.append(Paragraph(f"Date : {date}", styles['Normal']))

    elements.append(Spacer(1,20))

    data=[["Item","Qty","Price","Total"]]

    for item,qty,price in items:

        data.append([item,qty,price,qty*price])

    data.append(["","","Grand Total",total])

    table = Table(data)

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1f4e79")),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return buffer

# ---------------- SIDEBAR ----------------

st.sidebar.title("Billing Menu")

page = st.sidebar.radio(
"Navigation",
[
"Dashboard",
"Create Invoice",
"Invoice History",
"Customer Master",
"Product Master",
"GST Report"
]
)

# ---------------- DASHBOARD ----------------

if page=="Dashboard":

    st.title("Sales Dashboard")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    if df.empty:

        st.info("No sales data yet")

    else:

        total_revenue = df["total"].sum()

        total_invoices = len(df)

        col1,col2 = st.columns(2)

        col1.metric("Total Revenue", total_revenue)

        col2.metric("Total Invoices", total_invoices)

        st.subheader("Revenue by Customer")

        chart = df.groupby("customer")["total"].sum()

        st.bar_chart(chart)

# ---------------- CREATE INVOICE ----------------

elif page=="Create Invoice":

    st.title("Create Invoice")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")

    result = cursor.fetchone()

    invoice_no = 1001 if result[0] is None else result[0]+1

    st.subheader(f"Invoice No : {invoice_no}")

    customers = pd.read_sql("SELECT * FROM customers",conn)

    if not customers.empty:

        customer = st.selectbox("Customer",customers["name"])

    else:

        customer = st.text_input("Customer")

    invoice_date = st.date_input("Date",date.today())

    items=[]

    rows = st.number_input("Number of Items",1,10,1)

    for i in range(int(rows)):

        col1,col2,col3 = st.columns(3)

        with col1:

            item = st.text_input(f"Item {i+1}")

        with col2:

            qty = st.number_input(f"Qty {i+1}",1)

        with col3:

            price = st.number_input(f"Price {i+1}")

        items.append((item,qty,price))

    total = sum(q*p for _,q,p in items)

    st.write("Total :", total)

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
        (invoice_no,customer,str(invoice_date),total)
        )

        conn.commit()

        pdf = generate_pdf(invoice_no,customer,invoice_date,items,total)

        st.download_button(
        "Download Invoice PDF",
        data=pdf,
        file_name=f"invoice_{invoice_no}.pdf",
        mime="application/pdf"
        )

# ---------------- INVOICE HISTORY ----------------

elif page=="Invoice History":

    st.title("Invoice History")

    search = st.text_input("Search Invoice or Customer")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    if search:

        df = df[
            df["customer"].str.contains(search,case=False) |
            df["invoice_no"].astype(str).str.contains(search)
        ]

    st.dataframe(df)

    st.subheader("Edit Invoice")

    edit_id = st.number_input("Enter Invoice Number")

    new_customer = st.text_input("New Customer Name")

    if st.button("Update Invoice"):

        cursor.execute(
        "UPDATE invoices SET customer=? WHERE invoice_no=?",
        (new_customer,edit_id)
        )

        conn.commit()

        st.success("Invoice Updated")

# ---------------- CUSTOMER MASTER ----------------

elif page=="Customer Master":

    st.title("Customer Master")

    name = st.text_input("Customer Name")

    contact = st.text_input("Contact")

    gstin = st.text_input("GSTIN")

    if st.button("Add Customer"):

        cursor.execute(
        "INSERT INTO customers (name,contact,gstin) VALUES (?,?,?)",
        (name,contact,gstin)
        )

        conn.commit()

        st.success("Customer Added")

    df = pd.read_sql("SELECT * FROM customers",conn)

    st.dataframe(df)

# ---------------- PRODUCT MASTER ----------------

elif page=="Product Master":

    st.title("Product Master")

    name = st.text_input("Product Name")

    price = st.number_input("Price")

    if st.button("Add Product"):

        cursor.execute(
        "INSERT INTO products (name,price) VALUES (?,?)",
        (name,price)
        )

        conn.commit()

        st.success("Product Added")

    df = pd.read_sql("SELECT * FROM products",conn)

    st.dataframe(df)

# ---------------- GST REPORT ----------------

elif page=="GST Report":

    st.title("Monthly GST Sales Report")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    if df.empty:

        st.info("No sales data")

    else:

        df["date"] = pd.to_datetime(df["date"])

        report = df.groupby(df["date"].dt.month)["total"].sum()

        st.bar_chart(report)

        excel = io.BytesIO()

        df.to_excel(excel,index=False)

        st.download_button(
        "Download Excel Report",
        excel.getvalue(),
        file_name="gst_sales_report.xlsx"
        )
