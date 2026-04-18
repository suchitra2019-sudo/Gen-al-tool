import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date
import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="GST Billing Software", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("billing.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    contact TEXT,
    gstin TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no INTEGER,
    customer TEXT,
    date TEXT,
    total REAL
)
""")

conn.commit()

# ---------------- SIDEBAR ----------------
st.sidebar.title("Billing Menu")

page = st.sidebar.radio(
    "Navigation",
    ["Create Invoice", "Invoice History", "Customer Master", "Product Master"]
)

# ---------------- AUTO INVOICE ----------------
def get_invoice_no():
    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()[0]
    return 1001 if result is None else result + 1


# ---------------- PDF FUNCTION ----------------
def generate_pdf(company, address, gst, logo, invoice_no, date,
                 customer, contact, gstin, items, subtotal, GST, transport, total):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Logo
    if logo and os.path.exists(logo):
        elements.append(Image(logo, width=60, height=60))

    # Company
    elements.append(Paragraph(f"<b>{company}</b>", styles['Title']))
    elements.append(Paragraph(address, styles['Normal']))
    elements.append(Paragraph(f"GSTIN: {gst}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Invoice Info
    elements.append(Paragraph(f"Invoice No: {invoice_no}", styles['Normal']))
    elements.append(Paragraph(f"Date: {date}", styles['Normal']))
    elements.append(Spacer(1, 10))

    # Customer
    elements.append(Paragraph(f"Customer: {customer}", styles['Normal']))
    elements.append(Paragraph(f"Contact: {contact}", styles['Normal']))
    elements.append(Paragraph(f"GSTIN: {gstin}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Items Table
    data = [["Item", "Qty", "Price", "Total"]]
    for item, qty, price in items:
        data.append([item, qty, price, qty * price])

    table = Table(data)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Totals
    elements.append(Paragraph(f"Subtotal: {subtotal}", styles['Normal']))
    elements.append(Paragraph(f"GST (18%): {GST}", styles['Normal']))
    elements.append(Paragraph(f"Transport: {transport}", styles['Normal']))
    elements.append(Paragraph(f"<b>Total: {total}</b>", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    return buffer


# ====================================================
# CREATE INVOICE
# ====================================================
if page == "Create Invoice":

    st.title("GST Invoice Generator")

    invoice_no = get_invoice_no()
    st.subheader(f"Invoice No: {invoice_no}")

    # Company (Non Editable)
    company = "SHIVKRUTI ENTERPRISES"
    address = "BHIWANDI, THANE"
    gst = "27CFKPP2024L1Z7"

    st.write(company)
    st.write(address)

    # Customer
    customers = pd.read_sql("SELECT * FROM customers", conn)

    if not customers.empty:
        customer_name = st.selectbox("Customer", customers["name"])
        cust = customers[customers["name"] == customer_name].iloc[0]
        contact = cust["contact"]
        gstin = cust["gstin"]
    else:
        customer_name = st.text_input("Customer")
        contact = st.text_input("Contact")
        gstin = st.text_input("GSTIN")

    invoice_date = st.date_input("Invoice Date", date.today())

    # Products
    products = pd.read_sql("SELECT * FROM products", conn)

    items = []
    rows = st.number_input("Number of Items", 1, 10, 1)

    for i in range(int(rows)):
        col1, col2, col3 = st.columns(3)

        with col1:
            if not products.empty:
                product = st.selectbox(f"Product {i+1}", products["name"], key=i)
                price = products[products["name"] == product]["price"].values[0]
            else:
                product = st.text_input(f"Item {i+1}")
                price = st.number_input(f"Price {i+1}")

        with col2:
            qty = st.number_input(f"Qty {i+1}", 1)

        with col3:
            st.write("Price:", price)

        items.append((product, qty, price))

    transport = st.number_input("Transport", 0.0)

    # Calculations
    subtotal = sum(q * p for _, q, p in items)
    GST = subtotal * 0.18
    total = subtotal + GST + transport

    st.write("Subtotal:", subtotal)
    st.write("GST:", GST)
    st.write("Total:", total)

    # Generate
    if st.button("Generate Invoice"):

        cursor.execute(
            "INSERT INTO invoices (invoice_no, customer, date, total) VALUES (?,?,?,?)",
            (invoice_no, customer_name, str(invoice_date), total)
        )
        conn.commit()

        pdf = generate_pdf(
            company, address, gst, None,
            invoice_no, invoice_date,
            customer_name, contact, gstin,
            items, subtotal, GST, transport, total
        )

        st.success("Invoice Created")

        st.download_button(
            "Download PDF",
            data=pdf,
            file_name=f"invoice_{invoice_no}.pdf",
            mime="application/pdf"
        )


# ====================================================
# CUSTOMER MASTER
# ====================================================
elif page == "Customer Master":

    st.title("Customer Master")

    name = st.text_input("Customer Name")
    contact = st.text_input("Contact")
    gstin = st.text_input("GSTIN")

    if st.button("Add Customer"):
        cursor.execute(
            "INSERT INTO customers (name,contact,gstin) VALUES (?,?,?)",
            (name, contact, gstin)
        )
        conn.commit()
        st.success("Customer Added")

    df = pd.read_sql("SELECT * FROM customers", conn)
    st.dataframe(df)


# ====================================================
# PRODUCT MASTER
# ====================================================
elif page == "Product Master":

    st.title("Product Master")

    name = st.text_input("Product Name")
    price = st.number_input("Price")

    if st.button("Add Product"):
        cursor.execute(
            "INSERT INTO products (name,price) VALUES (?,?)",
            (name, price)
        )
        conn.commit()
        st.success("Product Added")

    df = pd.read_sql("SELECT * FROM products", conn)
    st.dataframe(df)


# ====================================================
# INVOICE HISTORY
# ====================================================
elif page == "Invoice History":

    st.title("Invoice History")

    df = pd.read_sql("SELECT * FROM invoices", conn)
    st.dataframe(df)

    delete_id = st.number_input("Invoice Number to Delete")

    if st.button("Delete Invoice"):
        cursor.execute("DELETE FROM invoices WHERE invoice_no=?", (delete_id,))
        conn.commit()
        st.success("Invoice Deleted")
