import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Professional GST Billing", layout="wide")

# ---------------- DATABASE ----------------

conn = sqlite3.connect("billing.db", check_same_thread=False)
cursor = conn.cursor()

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_no INTEGER,
customer TEXT,
date TEXT,
total REAL)
""")

conn.commit()

# ---------------- PDF GENERATOR ----------------

def generate_invoice_pdf(
company,
address,
gstin,
invoice_no,
invoice_date,
customer,
items,
total,
logo=None
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()

    elements = []

# COMPANY HEADER

    header=[]

    if logo:
        logo_img = Image(logo, width=80, height=50)
        header.append([logo_img, Paragraph(f"<b>{company}</b><br/>{address}<br/>GSTIN: {gstin}", styles['Normal'])])
    else:
        header.append(["", Paragraph(f"<b>{company}</b><br/>{address}<br/>GSTIN: {gstin}", styles['Normal'])])

    table = Table(header, colWidths=[100,400])
    elements.append(table)

    elements.append(Spacer(1,20))

    elements.append(Paragraph("<b>TAX INVOICE</b>", styles['Title']))

    elements.append(Spacer(1,10))

# INVOICE DETAILS

    details = Table([
        ["Invoice No", invoice_no, "Date", invoice_date],
        ["Customer", customer, "", ""]
    ])

    details.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.grey)
    ]))

    elements.append(details)

    elements.append(Spacer(1,20))

# ITEM TABLE

    data=[["Item","Qty","Price","Amount"]]

    for item,qty,price in items:
        data.append([item,qty,price,qty*price])

    data.append(["","","Grand Total",total])

    item_table = Table(data)

    item_table.setStyle(TableStyle([

        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2E5090")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),

        ("GRID",(0,0),(-1,-1),1,colors.grey),

        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(2,-1),(3,-1),"Helvetica-Bold")

    ]))

    elements.append(item_table)

    elements.append(Spacer(1,30))

    elements.append(Paragraph("Authorized Signature", styles['Normal']))

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
        st.info("No sales yet")
    else:

        col1,col2 = st.columns(2)

        col1.metric("Total Revenue", df["total"].sum())
        col2.metric("Total Invoices", len(df))

        chart = df.groupby("customer")["total"].sum()

        st.bar_chart(chart)

# ---------------- CREATE INVOICE ----------------

elif page=="Create Invoice":

    st.title("Create Invoice")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()

    invoice_no = 1001 if result[0] is None else result[0] + 1

    st.subheader(f"Invoice No : {invoice_no}")

# COMPANY

    st.sidebar.header("Company Settings")

    company = st.sidebar.text_input("Company Name","My Company")

    address = st.sidebar.text_area("Address","Mumbai")

    gstin = st.sidebar.text_input("Company GSTIN")

    logo = st.sidebar.file_uploader("Upload Company Logo")

# CUSTOMER

    customers = pd.read_sql("SELECT * FROM customers",conn)

    if not customers.empty:
        customer = st.selectbox("Customer", customers["name"])
    else:
        customer = st.text_input("Customer Name")

    invoice_date = st.date_input("Invoice Date", date.today())

# ITEMS

    items=[]

    rows = st.number_input("Number of Items",1,10,1)

    for i in range(int(rows)):

        col1,col2,col3 = st.columns(3)

        with col1:
            item = st.text_input(f"Item {i+1}")

        with col2:
            qty = st.number_input(f"Qty {i+1}",1)

        with col3:
            price = st.number_input(f"Price {i+1}",0.0)

        items.append((item,qty,price))

    total = sum(q*p for _,q,p in items)

    st.write("### Total :", total)

# GENERATE

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
        (invoice_no,customer,str(invoice_date),total)
        )

        conn.commit()

        pdf = generate_invoice_pdf(
            company,
            address,
            gstin,
            invoice_no,
            invoice_date,
            customer,
            items,
            total,
            logo
        )

        st.download_button(
        "Download Invoice PDF",
        pdf,
        file_name=f"invoice_{invoice_no}.pdf",
        mime="application/pdf"
        )

# ---------------- INVOICE HISTORY ----------------

elif page=="Invoice History":

    st.title("Invoice History")

    search = st.text_input("Search Invoice / Customer")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    if search:

        df = df[
            df["customer"].str.contains(search,case=False) |
            df["invoice_no"].astype(str).str.contains(search)
        ]

    st.dataframe(df)

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

    st.dataframe(pd.read_sql("SELECT * FROM customers",conn))

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

    st.dataframe(pd.read_sql("SELECT * FROM products",conn))

# ---------------- GST REPORT ----------------

elif page=="GST Report":

    st.title("GST Sales Report")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    if df.empty:
        st.info("No sales data")
    else:

        df["date"] = pd.to_datetime(df["date"])

        monthly = df.groupby(df["date"].dt.month)["total"].sum()

        st.bar_chart(monthly)

        excel = io.BytesIO()

        df.to_excel(excel,index=False)

        st.download_button(
        "Download GST Excel Report",
        excel.getvalue(),
        "gst_report.xlsx"
        )
