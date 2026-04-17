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
.main-title{font-size:32px;font-weight:bold;color:#1f4e79;}
.card{background:#ffffff;padding:20px;border-radius:10px;box-shadow:0 0 10px rgba(0,0,0,0.1);} 
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("billing.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,contact TEXT,gstin TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,price REAL)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_no INTEGER,customer TEXT,date TEXT,total REAL)
""")

conn.commit()

# ---------------- SIDEBAR ----------------
st.sidebar.title("Billing Menu")
page = st.sidebar.radio("Navigation",["Create Invoice","Invoice History","Customer Master","Product Master"])

# ====================================================
# HTML INVOICE TEMPLATE (FIXED)
# ====================================================

def generate_invoice_html(company,address,gst,logo,invoice_no,formatted_date,customer,contact,gstin,items,subtotal,GST,sgst,transport,total,kg):

    rows=""
    for desc,qty,price in items:
        rows += f"""
        <tr>
        <td>{desc}</td>
        <td>{qty}</td>
        <td>{price}</td>
        <td>{qty*price}</td>
        </tr>
        """

    logo_html = f'<img src="{logo}" width="120">' if logo else ""

    html=f"""
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
    </div>
    """

    return html

# ====================================================
# PDF GENERATOR (YOUR DESIGN FIXED)
# ====================================================

def generate_pdf(company,address,gst,logo,invoice_no,formatted_date,customer,contact,gstin,items,subtotal,GST,sgst,transport,total):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer,pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)

    styles = getSampleStyleSheet()
    elements = []

    # HEADER
    if logo:
        logo_img = Image(logo,width=60,height=60)
    else:
        logo_img = ""

    company_block = Paragraph(f"<b>{company}</b><br/>{address}<br/>GSTIN : {gst}",styles["Normal"])

    header = Table([[logo_img,company_block]],colWidths=[80,420])
    elements.append(header)
    elements.append(Spacer(1,20))

    # TITLE
    title_table = Table([["INVOICE",f"Invoice # {invoice_no}"]],colWidths=[350,150])
    title_table.setStyle(TableStyle([("FONTNAME",(0,0),(0,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(0,0),18),("ALIGN",(1,0),(1,0),"RIGHT")]))
    elements.append(title_table)
    elements.append(Spacer(1,20))

    # BILL TO
    bill_to = Table([["Bill To"],[customer],[contact],[f"GSTIN : {gstin}"]],colWidths=[500])
    elements.append(bill_to)
    elements.append(Spacer(1,20))

    # INFO TABLE (FIXED formatted_date)
    info = Table([["Invoice Date","Terms","Due Date"],[str(formatted_date),"Due on Receipt",str(formatted_date)]],colWidths=[166,166,166])
    info.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f4e79")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),1,colors.lightgrey)]))
    elements.append(info)
    elements.append(Spacer(1,25))

    # ITEM TABLE
    table_data=[["#","Item","Qty","Rate","Amount"]]
    i=1
    for desc,qty,price in items:
        table_data.append([i,desc,qty,price,qty*price])
        i+=1

    item_table=Table(table_data,colWidths=[40,220,70,80,90])
    item_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f4e79")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),1,colors.lightgrey)]))
    elements.append(item_table)
    elements.append(Spacer(1,20))

    # TOTALS
    totals=Table([["Sub Total",subtotal],["GST (18%)",GST],["SGST",sgst],["Transport",transport],["Total",total]],colWidths=[350,150])
    elements.append(totals)

    elements.append(Spacer(1,30))

    # SIGNATURE
    sign_path="sign.png"
    if os.path.exists(sign_path):
        sign=Image(sign_path,width=100,height=50)
        elements.append(sign)

    elements.append(Paragraph("<b>Authorized Signature</b>",styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ====================================================
# CREATE INVOICE
# ====================================================

if page=="Create Invoice":

    st.markdown('<div class="main-title">GST Invoice Generator</div>', unsafe_allow_html=True)

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result=cursor.fetchone()

    invoice_no=1001 if result[0] is None else result[0]+1

    st.subheader(f"Invoice No : {invoice_no}")

    company=st.sidebar.text_input("Company Name","SHIVKRUTI ENTERPRISES")
    address=st.sidebar.text_area("Address")
    gst=st.sidebar.text_input("GSTIN")

    logo_path="logo.png"

    customer_name=st.text_input("Customer")
    contact=st.text_input("Contact")
    gstin=st.text_input("GSTIN")

    invoice_date = st.date_input("Invoice Date", date.today())
    formatted_date = invoice_date.strftime("%d-%m-%Y")

    kg = st.text_input("Weight (KG)")

    items=[]
    rows=st.number_input("Items",1,5,1)

    for i in range(int(rows)):
        name=st.text_input(f"Item {i+1}")
        qty=st.number_input(f"Qty {i+1}",1)
        price=st.number_input(f"Price {i+1}")
        items.append((name,qty,price))

    transport=st.number_input("Transport")

    subtotal=sum(q*p for _,q,p in items)
    GST=subtotal*0.18
    sgst=0
    total=subtotal+GST+transport

    if st.button("Preview"):
        html=generate_invoice_html(company,address,gst,logo_path,invoice_no,formatted_date,customer_name,contact,gstin,items,subtotal,GST,sgst,transport,total,kg)
        components.html(html,height=900)

    if st.button("Generate PDF"):
        pdf=generate_pdf(company,address,gst,logo_path,invoice_no,formatted_date,customer_name,contact,gstin,items,subtotal,GST,sgst,transport,total)
        st.download_button("Download PDF",pdf,file_name=f"invoice_{invoice_no}.pdf")

# OTHER PAGES SAME AS BEFORE
elif page=="Customer Master":
    st.title("Customer Master")
elif page=="Product Master":
    st.title("Product Master")
elif page=="Invoice History":
    st.title("Invoice History")
