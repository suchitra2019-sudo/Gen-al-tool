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
page = st.sidebar.radio("Navigation", ["Create Invoice","Invoice History","Customer Master","Product Master"])

# ---------------- HTML GENERATOR ----------------
def generate_invoice_html(company,address,gst,logo,invoice_no,formatted_date,customer,contact,gstin,items,subtotal,GST,sgst,transport,total,kg):
    rows = ""
    for desc,qty,price in items:
        rows += f"""
        <tr>
        <td>{desc}</td>
        <td>{qty}</td>
        <td>{price}</td>
        <td>{qty*price}</td>
        </tr>
        """

    logo_html = f'<img src="{logo}" width="80"/>' if os.path.exists(logo) else ""

    stamp_path = "stamp.png"
    sign_path = "sign.png"

    html = f"""
    <style>
    body{{font-family:Arial}}
    .invoice{{width:800px;margin:auto;border:1px solid #ddd;padding:20px}}
    table{{width:100%;border-collapse:collapse}}
    th,td{{border:1px solid #ccc;padding:8px}}
    th{{background:#1f4e79;color:white}}
    .header{{display:flex;justify-content:space-between}}
    </style>

    <div class="invoice">
    <div class="header">

    <div>
    {logo_html}
    <h2>{company}</h2>
    {address}<br>
    GSTIN: {gst}
    </div>

    <div>
    <h3>TAX INVOICE</h3>
    Invoice No: {invoice_no}<br>
    Date: {formatted_date}
    </div>

    </div>

    <hr>

    <b>Bill To</b><br>
    {customer}<br>
    Contact: {contact}<br>
    GSTIN: {gstin}<br>
    <b>Weight (KG):</b> {kg}

    <table>
    <tr>
    <th>Description</th>
    <th>Qty</th>
    <th>Price</th>
    <th>Total</th>
    </tr>
    {rows}
    <tr><td colspan=3>Subtotal</td><td>{subtotal}</td></tr>
    <tr><td colspan=3>GST</td><td>{GST}</td></tr>
    <tr><td colspan=3>SGST</td><td>{sgst}</td></tr>
    <tr><td colspan=3>Transport</td><td>{transport}</td></tr>
    <tr><td colspan=3><b>Grand Total</b></td><td><b>{total}</b></td></tr>
    </table>

    <div style="display:flex; justify-content:space-between; margin-top:40px;">
    <div>
        <img src="{stamp_path}" width="120"><br>
        <b>Company Stamp</b>
    </div>
    <div>
        <img src="{sign_path}" width="120"><br>
        <b>Authorized Signature</b>
    </div>
    </div>

    </div>
    """

    return html

# ---------------- PDF GENERATOR ----------------
def generate_pdf(company,address,gst,logo,invoice_no,formatted_date,customer,contact,gstin,items,subtotal,GST,sgst,transport,total):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    if os.path.exists(logo):
        logo_img = Image(logo, width=60, height=60)
    else:
        logo_img = ""

    company_block = Paragraph(f"<b>{company}</b><br/>{address}<br/>GSTIN : {gst}", styles["Normal"])
    header = Table([[logo_img, company_block]])
    elements.append(header)
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Invoice #{invoice_no}", styles["Title"]))
    elements.append(Paragraph(f"Date: {formatted_date}", styles["Normal"]))
    elements.append(Spacer(1,20))

    table_data = [["Item","Qty","Rate","Amount"]]
    for desc,qty,price in items:
        table_data.append([desc,qty,price,qty*price])

    table = Table(table_data)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))
    elements.append(table)
    elements.append(Spacer(1,20))

    totals = Table([
        ["Subtotal",subtotal],
        ["GST",GST],
        ["Transport",transport],
        ["Total",total]
    ])
    elements.append(totals)

    # Stamp & Signature
    stamp_path = "stamp.png"
    sign_path = "sign.png"

    stamp = Image(stamp_path, width=80, height=50) if os.path.exists(stamp_path) else ""
    sign = Image(sign_path, width=80, height=50) if os.path.exists(sign_path) else ""

    footer = Table([[stamp, "", sign],["Stamp","","Signature"]])
    elements.append(footer)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------- CREATE INVOICE ----------------
if page == "Create Invoice":
    st.title("GST Invoice Generator")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()
    invoice_no = 1001 if result[0] is None else result[0] + 1

    company = st.sidebar.text_input("Company Name","SHIVKRUTI ENTERPRISES")
    address = st.sidebar.text_area("Address")
    gst = st.sidebar.text_input("GSTIN")

    logo_path = "logo.png"

    customer_name = st.text_input("Customer Name")
    contact = st.text_input("Contact")
    gstin = st.text_input("Customer GSTIN")

    invoice_date = st.date_input("Invoice Date", date.today())
    formatted_date = invoice_date.strftime("%d-%m-%Y")

    kg = st.text_input("Weight (KG)")

    items = []
    rows = st.number_input("Items",1,5,1)

    for i in range(int(rows)):
        name = st.text_input(f"Item {i+1}")
        qty = st.number_input(f"Qty {i+1}",1)
        price = st.number_input(f"Price {i+1}")
        items.append((name,qty,price))

    transport = st.number_input("Transport")

    subtotal = sum(q*p for _,q,p in items)
    GST = subtotal * 0.18
    sgst = 0
    total = subtotal + GST 

    if st.button("Preview"):
        html = generate_invoice_html(company,address,gst,logo_path,invoice_no,formatted_date,customer_name,contact,gstin,items,subtotal,GST,sgst,transport,total,kg)
        components.html(html, height=900)

    if st.button("Generate PDF"):
        pdf = generate_pdf(company,address,gst,logo_path,invoice_no,formatted_date,customer_name,contact,gstin,items,subtotal,GST,sgst,transport,total)
        st.download_button("Download", pdf, file_name="invoice.pdf")

# ---------------- OTHER PAGES ----------------
elif page == "Customer Master":
    st.title("Customer Master")

elif page == "Product Master":
    st.title("Product Master")

elif page == "Invoice History":
    st.title("Invoice History")
