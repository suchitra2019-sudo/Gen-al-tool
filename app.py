import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date
import io
import base64

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
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

page = st.sidebar.radio(
"Navigation",
[
"Create Invoice",
"Invoice History",
"Customer Master",
"Product Master"
]
)

# ---------------- HTML PREVIEW ----------------

def generate_invoice_html(company,address,gst,logo,
invoice_no,date,customer,contact,gstin,
items,subtotal,cgst,sgst,transport,total):

    rows=""

    for desc,qty,price in items:

        rows+=f"""
<tr>
<td>{desc}</td>
<td>{qty}</td>
<td>{price}</td>
<td>{qty*price}</td>
</tr>
"""

    html=f"""
<style>

body{{font-family:Arial}}

.invoice{{width:800px;margin:auto;border:1px solid #ddd;padding:20px}}

table{{width:100%;border-collapse:collapse}}

th,td{{border:1px solid #ccc;padding:8px}}

th{{background:#1f4e79;color:white}}

</style>

<div class="invoice">

<h2>{company}</h2>

{address}<br>
GSTIN : {gst}

<hr>

<h3>TAX INVOICE</h3>

Invoice No : {invoice_no}<br>
Date : {date}

<br>

<b>Bill To</b><br>
{customer}<br>
Contact : {contact}<br>
GSTIN : {gstin}

<table>

<tr>
<th>Description</th>
<th>Qty</th>
<th>Price</th>
<th>Total</th>
</tr>

{rows}

<tr><td colspan=3>Subtotal</td><td>{subtotal}</td></tr>
<tr><td colspan=3>CGST</td><td>{cgst}</td></tr>
<tr><td colspan=3>SGST</td><td>{sgst}</td></tr>
<tr><td colspan=3>Transport</td><td>{transport}</td></tr>
<tr><td colspan=3><b>Grand Total</b></td><td><b>{total}</b></td></tr>

</table>

</div>
"""

    return html

# ---------------- PDF GENERATOR ----------------

def generate_pdf(company,address,gst,logo_file,
invoice_no,date,customer,contact,gstin,
items,subtotal,cgst,sgst,transport,total):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer,pagesize=A4)

    styles = getSampleStyleSheet()

    elements = []

    # COMPANY HEADER

    elements.append(Paragraph(f"<b>{company}</b>",styles['Title']))
    elements.append(Paragraph(address,styles['Normal']))
    elements.append(Paragraph(f"GSTIN : {gst}",styles['Normal']))

    elements.append(Spacer(1,20))

    # INVOICE INFO

    info = Table([
        ["Invoice No",invoice_no,"Date",str(date)],
        ["Customer",customer,"Contact",contact],
        ["GSTIN",gstin,"",""]
    ])

    info.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.grey)
    ]))

    elements.append(info)

    elements.append(Spacer(1,20))

    # ITEMS TABLE

    data=[["Description","Qty","Price","Total"]]

    for desc,qty,price in items:

        data.append([desc,qty,price,qty*price])

    data.append(["","","Subtotal",subtotal])
    data.append(["","","CGST",cgst])
    data.append(["","","SGST",sgst])
    data.append(["","","Transport",transport])
    data.append(["","","Grand Total",total])

    table = Table(data)

    table.setStyle(TableStyle([

        ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1f4e79")),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(2,-1),(-1,-1),'Helvetica-Bold')

    ]))

    elements.append(table)

    elements.append(Spacer(1,40))

    elements.append(Paragraph("Authorized Signature",styles['Normal']))

    doc.build(elements)

    buffer.seek(0)

    return buffer

# ---------------- CREATE INVOICE ----------------

if page=="Create Invoice":

    st.title("GST Invoice Generator")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result=cursor.fetchone()

    invoice_no=1001 if result[0] is None else result[0]+1

    st.subheader(f"Invoice No : {invoice_no}")

    st.sidebar.header("Company Settings")

    company=st.sidebar.text_input("Company Name","My Company")
    address=st.sidebar.text_area("Address","Mumbai")
    gst=st.sidebar.text_input("GSTIN")

    logo_file=st.sidebar.file_uploader("Upload Company Logo")

    # CUSTOMER

    customers=pd.read_sql("SELECT * FROM customers",conn)

    if not customers.empty:

        customer=st.selectbox("Customer",customers["name"])

        cust=customers[customers["name"]==customer].iloc[0]

        contact=cust["contact"]
        gstin=cust["gstin"]

    else:

        customer=st.text_input("Customer")
        contact=st.text_input("Contact")
        gstin=st.text_input("GSTIN")

    invoice_date=st.date_input("Invoice Date",date.today())

    # PRODUCTS

    products=pd.read_sql("SELECT * FROM products",conn)

    items=[]

    rows=st.number_input("Number of Items",1,10,1)

    for i in range(int(rows)):

        c1,c2,c3=st.columns(3)

        with c1:

            if not products.empty:

                product=st.selectbox(f"Product {i+1}",products["name"],key=i)

                price=products[products["name"]==product]["price"].values[0]

            else:

                product=st.text_input(f"Item {i+1}")
                price=st.number_input(f"Price {i+1}")

        with c2:

            qty=st.number_input(f"Qty {i+1}",1)

        with c3:

            st.write("Price:",price)

        items.append((product,qty,price))

    transport=st.number_input("Transport",0.0)

    subtotal=sum(q*p for _,q,p in items)

    cgst=subtotal*0.09
    sgst=subtotal*0.09

    total=subtotal+cgst+sgst+transport

    st.write("Subtotal:",subtotal)
    st.write("CGST:",cgst)
    st.write("SGST:",sgst)
    st.write("Total:",total)

    html=generate_invoice_html(
    company,address,gst,logo_file,
    invoice_no,invoice_date,
    customer,contact,gstin,
    items,subtotal,cgst,sgst,transport,total
    )

    if st.toggle("Invoice Preview"):

        components.html(html,height=900)

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
        (invoice_no,customer,str(invoice_date),total)
        )

        conn.commit()

        pdf=generate_pdf(
        company,address,gst,logo_file,
        invoice_no,invoice_date,
        customer,contact,gstin,
        items,subtotal,cgst,sgst,transport,total
        )

        st.download_button(
        "Download Invoice PDF",
        data=pdf,
        file_name=f"invoice_{invoice_no}.pdf",
        mime="application/pdf"
        )

# ---------------- CUSTOMER MASTER ----------------

elif page=="Customer Master":

    st.title("Customer Master")

    name=st.text_input("Customer Name")
    contact=st.text_input("Contact")
    gstin=st.text_input("GSTIN")

    if st.button("Add Customer"):

        cursor.execute(
        "INSERT INTO customers (name,contact,gstin) VALUES (?,?,?)",
        (name,contact,gstin)
        )

        conn.commit()

        st.success("Customer Added")

    df=pd.read_sql("SELECT * FROM customers",conn)

    st.dataframe(df)

# ---------------- PRODUCT MASTER ----------------

elif page=="Product Master":

    st.title("Product Master")

    name=st.text_input("Product Name")
    price=st.number_input("Price")

    if st.button("Add Product"):

        cursor.execute(
        "INSERT INTO products (name,price) VALUES (?,?)",
        (name,price)
        )

        conn.commit()

        st.success("Product Added")

    df=pd.read_sql("SELECT * FROM products",conn)

    st.dataframe(df)

# ---------------- INVOICE HISTORY ----------------

elif page=="Invoice History":

    st.title("Invoice History")

    df=pd.read_sql("SELECT * FROM invoices",conn)

    st.dataframe(df)
