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

# ---------------- STYLE ----------------
st.markdown("""
<style>
.main-title{
    font-size:32px;
    font-weight:bold;
    color:#1f4e79;
}
</style>
""", unsafe_allow_html=True)

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

# ---------------- SIDEBAR ----------------
st.sidebar.title("Billing Menu")
page = st.sidebar.radio("Navigation", [
    "Create Invoice",
    "Invoice History",
    "Customer Master",
    "Product Master"
])

# ====================================================
# HTML GENERATOR
# ====================================================
def generate_invoice_html(company, address, gst, logo,
                          invoice_no, date, customer, contact, gstin,
                          items, subtotal, GST, sgst, transport, total):

    rows = ""
    for desc, qty, price in items:
        rows += f"""
        <tr>
        <td>{desc}</td>
        <td>{qty}</td>
        <td>{price}</td>
        <td>{qty*price}</td>
        </tr>
        """

    logo_html = f'<img src="{logo}" width="120">' if logo else ""

    return f"""
    <div>
    <h2>{company}</h2>
    <p>{address}<br>GSTIN: {gst}</p>
    <h3>Invoice #{invoice_no}</h3>
    <p>{customer} | {contact} | {gstin}</p>

    <table border="1" width="100%">
    <tr>
    <th>Description</th><th>Qty</th><th>Price</th><th>Total</th>
    </tr>
    {rows}
    </table>

    <p>Total: {total}</p>
    </div>
    """

# ====================================================
# PDF GENERATOR (FIXED)
# ====================================================
def generate_pdf(company, address, gst, logo,
                 invoice_no, date, customer, contact, gstin,
                 items, subtotal, GST, sgst, transport, total):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    if logo and os.path.exists(logo):
        logo_img = Image(logo, width=60, height=60)
    else:
        logo_img = Spacer(1, 1)

    elements.append(Table([[logo_img, company]]))
    elements.append(Spacer(1, 20))

    # Title
    elements.append(Paragraph(f"<b>Invoice #{invoice_no}</b>", styles["Title"]))
    elements.append(Spacer(1, 20))

    # Items
    table_data = [["#", "Item", "Qty", "Rate", "Amount"]]
    i = 1

    for desc, qty, price in items:
        table_data.append([i, desc, qty, price, qty * price])
        i += 1

    elements.append(Table(table_data))
    elements.append(Spacer(1, 20))

    # Totals
    totals = [
        ["Subtotal", subtotal],
        ["GST", GST],
        ["SGST", sgst],
        ["Transport", transport],
        ["Total", total]
    ]

    elements.append(Table(totals))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ====================================================
# CREATE INVOICE
# ====================================================
if page == "Create Invoice":

    st.title("GST Invoice Generator")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()
    invoice_no = 1001 if result[0] is None else result[0] + 1

    st.subheader(f"Invoice No: {invoice_no}")

    company = st.text_input("Company Name")
    address = st.text_area("Address")
    gst = st.text_input("GSTIN")
    logo_path = st.text_input("Logo Path")

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

    invoice_date = st.date_input("Date", date.today())

    # Items
    items = []
    rows = st.number_input("Items", 1, 10, 1)

    for i in range(int(rows)):
        product = st.text_input(f"Item {i+1}")
        qty = st.number_input(f"Qty {i+1}", 1)
        price = st.number_input(f"Price {i+1}", 0.0)
        items.append((product, qty, price))

    transport = st.number_input("Transport", 0.0)

    subtotal = sum(q * p for _, q, p in items)
    GST = subtotal * 0.18
    sgst = 0
    total = subtotal + GST + transport

    st.write("Total:", total)

    if st.button("Generate Invoice"):

        cursor.execute(
            "INSERT INTO invoices VALUES (NULL,?,?,?,?)",
            (invoice_no, customer_name, str(invoice_date), total)
        )
        conn.commit()

        pdf = generate_pdf(
            company, address, gst, logo_path,
            invoice_no, invoice_date,
            customer_name, contact, gstin,
            items, subtotal, GST, sgst, transport, total
        )

        st.download_button(
            "Download PDF",
            data=pdf,
            file_name="invoice.pdf"
        )
