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
.card{
background:#ffffff;
padding:20px;
border-radius:10px;
box-shadow:0 0 10px rgba(0,0,0,0.1);
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

page = st.sidebar.radio(
"Navigation",
[
"Create Invoice",
"Invoice History",
"Customer Master",
"Product Master"
]
)

# ====================================================
# HTML INVOICE TEMPLATE
# ====================================================

def generate_invoice_html(company,address,gst,logo,
invoice_no,date,customer,contact,gstin,
items,subtotal,cgst,sgst,transport,total):

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

    logo_html=""

    if logo:
        logo_html=f'<img src="{logo}" width="120">'

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
    Date: {date}
    </div>

    </div>

    <hr>

    <b>Bill To</b><br>
    {customer}<br>
    Contact: {contact}<br>
    GSTIN: {gstin}

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


# ====================================================
# ZOHO STYLE PDF GENERATOR
# ====================================================

def generate_pdf(company,address,gst,logo,
invoice_no,date,customer,contact,gstin,
items,subtotal,cgst,sgst,transport,total):

    buffer=io.BytesIO()

    doc=SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles=getSampleStyleSheet()
    elements=[]

# ---------------- HEADER ----------------

    header_data=[]

    if logo:
        logo_img=Image(logo,width=80,height=50)
    else:
        logo_img=""

    company_info=Paragraph(
        f"<b>{company}</b><br/>{address}<br/>GSTIN : {gst}",
        styles["Normal"]
    )

    header_data.append([logo_img,company_info])

    header_table=Table(header_data,colWidths=[100,400])

    elements.append(header_table)
    elements.append(Spacer(1,20))

# ---------------- TITLE ----------------

    title_table=Table([["TAX INVOICE"]],colWidths=[500])

    title_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0),colors.HexColor("#1f4e79")),
        ("TEXTCOLOR",(0,0),(0,0),colors.white),
        ("ALIGN",(0,0),(0,0),"CENTER"),
        ("FONTSIZE",(0,0),(0,0),16),
        ("BOTTOMPADDING",(0,0),(0,0),10),
        ("TOPPADDING",(0,0),(0,0),10)
    ]))

    elements.append(title_table)
    elements.append(Spacer(1,20))

# ---------------- CUSTOMER INFO ----------------

    info_table=Table([

        ["Invoice No",invoice_no,"Invoice Date",str(date)],
        ["Customer",customer,"Contact",contact],
        ["Customer GSTIN",gstin,"",""]

    ],colWidths=[120,180,120,160])

    info_table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.lightgrey),
        ("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),
        ("BACKGROUND",(2,0),(2,-1),colors.whitesmoke)
    ]))

    elements.append(info_table)
    elements.append(Spacer(1,25))

# ---------------- ITEM TABLE ----------------

    item_data=[["Item Description","Qty","Rate","Amount"]]

    for desc,qty,price in items:
        item_data.append([desc,qty,price,qty*price])

    item_data.append(["","","Subtotal",subtotal])
    item_data.append(["","","CGST (9%)",cgst])
    item_data.append(["","","SGST (9%)",sgst])
    item_data.append(["","","Transport",transport])
    item_data.append(["","","Grand Total",total])

    item_table=Table(item_data,colWidths=[240,80,100,120])

    item_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f4e79")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.grey),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ALIGN",(1,1),(-1,-1),"CENTER"),
        ("FONTNAME",(2,-1),(3,-1),"Helvetica-Bold")
    ]))

    elements.append(item_table)
    elements.append(Spacer(1,30))

# ---------------- FOOTER ----------------

elements.append(Spacer(1,40))

    elements.append(Paragraph("Payment Terms: Due within 15 days", styles["Normal"]))
    elements.append(Paragraph("Bank: ABC Bank", styles["Normal"]))
    elements.append(Paragraph("Account No: 1234567890", styles["Normal"]))

    elements.append(Spacer(1,30))

    elements.append(Paragraph("<b>Authorized Signature</b>", styles["Normal"]))

# ---------------- BUILD PDF ----------------

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

    st.sidebar.header("Company Settings")

    company=st.sidebar.text_input("Company Name","My Company")
    address=st.sidebar.text_area("Address","Mumbai")
    gst=st.sidebar.text_input("GSTIN","27ABCDE1234F1Z5")

    logo_file=st.sidebar.file_uploader("Upload Company Logo")

    logo_path=None

    if logo_file:
        logo_path=logo_file

# Customer

    customers=pd.read_sql("SELECT * FROM customers",conn)

    if not customers.empty:

        customer_name=st.selectbox("Customer",customers["name"])

        cust=customers[customers["name"]==customer_name].iloc[0]

        contact=cust["contact"]
        gstin=cust["gstin"]

    else:

        customer_name=st.text_input("Customer")
        contact=st.text_input("Contact")
        gstin=st.text_input("GSTIN")

    invoice_date=st.date_input("Invoice Date",date.today())

# Products

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
            st.write("Price :",price)

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

# Preview

    if st.toggle("Show Invoice Preview"):

        html=generate_invoice_html(
        company,address,gst,logo_path,
        invoice_no,invoice_date,
        customer_name,contact,gstin,
        items,subtotal,cgst,sgst,transport,total
        )

        components.html(html,height=900)

# Generate

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
        (invoice_no,customer_name,str(invoice_date),total)
        )

        conn.commit()

        pdf=generate_pdf(
        company,address,gst,logo_path,
        invoice_no,invoice_date,
        customer_name,contact,gstin,
        items,subtotal,cgst,sgst,transport,total
        )

        st.success("Invoice Created")

        st.download_button(
        label="Download Invoice PDF",
        data=pdf,
        file_name=f"invoice_{invoice_no}.pdf",
        mime="application/pdf"
        )

# ====================================================
# CUSTOMER MASTER
# ====================================================

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

# ====================================================
# PRODUCT MASTER
# ====================================================

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

# ====================================================
# INVOICE HISTORY
# ====================================================

elif page=="Invoice History":

    st.title("Invoice History")

    df=pd.read_sql("SELECT * FROM invoices",conn)
    st.dataframe(df)

    delete_id=st.number_input("Invoice Number to Delete")

    if st.button("Delete Invoice"):

        cursor.execute(
        "DELETE FROM invoices WHERE invoice_no=?",
        (delete_id,)
        )

        conn.commit()

        st.success("Invoice Deleted")
