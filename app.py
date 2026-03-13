import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date
from weasyprint import HTML
import tempfile
import base64

st.set_page_config(page_title="GST Billing Software", layout="wide")

# ==============================
# DATABASE
# ==============================

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

# ==============================
# SIDEBAR
# ==============================

st.sidebar.title("Billing Menu")

page = st.sidebar.radio(
"Navigation",
[
"Create Invoice",
"Invoice History",
"Customer Master",
"Product Master"
]
)

# ==============================
# HTML + CSS INVOICE TEMPLATE
# ==============================

def generate_invoice_html(data):

    html = f"""
<!DOCTYPE html>
<html>

<head>

<style>

body {{
font-family: Arial;
margin:40px;
}}

.invoice-box {{
max-width:900px;
margin:auto;
padding:30px;
border:1px solid #eee;
}}

.header {{
display:flex;
justify-content:space-between;
}}

.logo {{
height:70px;
}}

.company {{
text-align:right;
}}

.title {{
text-align:center;
font-size:28px;
margin-top:10px;
margin-bottom:20px;
color:#1f4e79;
font-weight:bold;
}}

.info-table {{
width:100%;
margin-bottom:20px;
}}

.info-table td {{
padding:6px;
}}

.items {{
width:100%;
border-collapse:collapse;
}}

.items th {{
background:#1f4e79;
color:white;
padding:10px;
border:1px solid #ddd;
}}

.items td {{
padding:10px;
border:1px solid #ddd;
text-align:center;
}}

.total-box {{
margin-top:20px;
width:40%;
float:right;
}}

.total-box table {{
width:100%;
}}

.total-box td {{
padding:8px;
}}

.grand-total {{
font-size:18px;
font-weight:bold;
border-top:2px solid black;
}}

.footer {{
margin-top:80px;
display:flex;
justify-content:space-between;
}}

</style>

</head>

<body>

<div class="invoice-box">

<div class="header">

<img src="{data['logo']}" class="logo">

<div class="company">
<b>{data['company']}</b><br>
{data['address']}<br>
GSTIN: {data['gst']}
</div>

</div>

<div class="title">TAX INVOICE</div>

<table class="info-table">

<tr>

<td>
<b>Bill To</b><br>
{data['customer']}<br>
Contact: {data['contact']}<br>
GSTIN: {data['gstin']}
</td>

<td align="right">
<b>Invoice No:</b> {data['invoice_no']}<br>
<b>Date:</b> {data['date']}
</td>

</tr>

</table>

<table class="items">

<tr>
<th>Description</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

{data['rows']}

</table>

<div class="total-box">

<table>

<tr>
<td>Subtotal</td>
<td align="right">{data['subtotal']}</td>
</tr>

<tr>
<td>CGST</td>
<td align="right">{data['cgst']}</td>
</tr>

<tr>
<td>SGST</td>
<td align="right">{data['sgst']}</td>
</tr>

<tr>
<td>Transport</td>
<td align="right">{data['transport']}</td>
</tr>

<tr class="grand-total">
<td>Grand Total</td>
<td align="right">{data['total']}</td>
</tr>

</table>

</div>

<div class="footer">

<div>
Thank you for your business!
</div>

<div>
Authorized Signature
</div>

</div>

</div>

</body>
</html>
"""

    return html

# ==============================
# PDF GENERATOR
# ==============================

def generate_pdf(html):

    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    HTML(string=html).write_pdf(pdf_file.name)

    return pdf_file.name

# ==============================
# CREATE INVOICE
# ==============================

if page == "Create Invoice":

    st.title("GST Invoice Generator")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()

    invoice_no = 1001 if result[0] is None else result[0] + 1

    st.subheader(f"Invoice No : {invoice_no}")

    st.sidebar.header("Company Settings")

    company = st.sidebar.text_input("Company Name","My Company")
    address = st.sidebar.text_area("Address","Mumbai")
    gst = st.sidebar.text_input("GSTIN")

    logo_file = st.sidebar.file_uploader("Upload Logo")

    logo_data = ""

    if logo_file:

        logo_bytes = logo_file.read()

        logo_data = "data:image/png;base64," + base64.b64encode(logo_bytes).decode()

    customers = pd.read_sql("SELECT * FROM customers",conn)

    if not customers.empty:

        customer = st.selectbox("Customer",customers["name"])

        cust = customers[customers["name"]==customer].iloc[0]

        contact = cust["contact"]
        gstin = cust["gstin"]

    else:

        customer = st.text_input("Customer")
        contact = st.text_input("Contact")
        gstin = st.text_input("GSTIN")

    invoice_date = st.date_input("Invoice Date",date.today())

    products = pd.read_sql("SELECT * FROM products",conn)

    items = []

    rows = st.number_input("Number of Items",1,10,1)

    for i in range(int(rows)):

        col1,col2,col3 = st.columns(3)

        with col1:

            if not products.empty:

                product = st.selectbox(f"Product {i+1}",products["name"],key=i)

                price = products[products["name"]==product]["price"].values[0]

            else:

                product = st.text_input(f"Item {i+1}")

                price = st.number_input(f"Price {i+1}")

        with col2:

            qty = st.number_input(f"Qty {i+1}",1)

        with col3:

            st.write("Price:",price)

        items.append((product,qty,price))

    transport = st.number_input("Transport",0.0)

    subtotal = sum(q*p for _,q,p in items)

    cgst = subtotal * 0.09
    sgst = subtotal * 0.09

    total = subtotal + cgst + sgst + transport

    st.write("Subtotal:",subtotal)
    st.write("CGST:",cgst)
    st.write("SGST:",sgst)
    st.write("Total:",total)

    # TABLE ROWS

    rows_html = ""

    for item,qty,price in items:

        rows_html += f"""
<tr>
<td>{item}</td>
<td>{qty}</td>
<td>{price}</td>
<td>{qty*price}</td>
</tr>
"""

    data = {

    "logo":logo_data,
    "company":company,
    "address":address,
    "gst":gst,
    "invoice_no":invoice_no,
    "date":invoice_date,
    "customer":customer,
    "contact":contact,
    "gstin":gstin,
    "rows":rows_html,
    "subtotal":subtotal,
    "cgst":cgst,
    "sgst":sgst,
    "transport":transport,
    "total":total

    }

    html = generate_invoice_html(data)

    if st.toggle("Invoice Preview"):

        components.html(html,height=900)

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
        (invoice_no,customer,str(invoice_date),total)
        )

        conn.commit()

        pdf_path = generate_pdf(html)

        with open(pdf_path,"rb") as f:

            st.download_button(
            "Download Professional Invoice PDF",
            f,
            file_name=f"Invoice_{invoice_no}.pdf",
            mime="application/pdf"
            )

# ==============================
# CUSTOMER MASTER
# ==============================

elif page == "Customer Master":

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

# ==============================
# PRODUCT MASTER
# ==============================

elif page == "Product Master":

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

# ==============================
# INVOICE HISTORY
# ==============================

elif page == "Invoice History":

    st.title("Invoice History")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    st.dataframe(df)
