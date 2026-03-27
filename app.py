# ✅ FULL UPDATED STREAMLIT INVOICE APP WITH:
# - Static company settings
# - Logo saved
# - Editable settings page
# - Clean structure

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

# ✅ COMPANY TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS company(
id INTEGER PRIMARY KEY,
name TEXT,
address TEXT,
gst TEXT,
logo TEXT)
""")

cursor.execute("SELECT COUNT(*) FROM company")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
    INSERT INTO company VALUES (
    1,
    'SHIVKRUTI ENTERPRISES',
    'Your Address Here',
    '27CFKPP2024L1Z7',
    'logo.png')
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
"Product Master",
"Company Settings"
]
)

# ====================================================
# PDF GENERATOR
# ====================================================

def generate_pdf(company,address,gst,logo,
invoice_no,date,customer,contact,gstin,
items,subtotal,GST,sgst,transport,total):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    if logo and os.path.exists(logo):
        logo_img = Image(logo,width=60,height=60)
    else:
        logo_img = ""

    header = Table([[logo_img, Paragraph(f"<b>{company}</b><br/>{address}<br/>GSTIN : {gst}", styles["Normal"])]])
    elements.append(header)
    elements.append(Spacer(1,20))

    table_data=[["Item","Qty","Rate","Amount"]]

    for desc,qty,price in items:
        table_data.append([desc,qty,price,qty*price])

    table_data.append(["","","Total",total])

    table=Table(table_data)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return buffer

# ====================================================
# CREATE INVOICE
# ====================================================

if page=="Create Invoice":

    company_data = pd.read_sql("SELECT * FROM company WHERE id=1", conn).iloc[0]

    company = company_data["name"]
    address = company_data["address"]
    gst = company_data["gst"]
    logo_path = company_data["logo"]

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result=cursor.fetchone()
    invoice_no=1001 if result[0] is None else result[0]+1

    st.subheader(f"Invoice No : {invoice_no}")

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
    GST=subtotal*0.18
    total=subtotal+GST+transport

    st.write("Total:",total)

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
        items,subtotal,GST,0,transport,total
        )

        st.download_button("Download PDF",pdf,file_name="invoice.pdf")

# ====================================================
# COMPANY SETTINGS
# ====================================================

elif page=="Company Settings":

    data = pd.read_sql("SELECT * FROM company WHERE id=1", conn).iloc[0]

    name = st.text_input("Company Name", data["name"])
    address = st.text_area("Address", data["address"])
    gst = st.text_input("GSTIN", data["gst"])

    logo_file = st.file_uploader("Upload Logo")
    logo_path = data["logo"]

    if logo_file:
        with open("logo.png", "wb") as f:
            f.write(logo_file.read())
        logo_path = "logo.png"

    if st.button("Save Settings"):

        cursor.execute("""
        UPDATE company
        SET name=?, address=?, gst=?, logo=?
        WHERE id=1
        """, (name, address, gst, logo_path))

        conn.commit()

        st.success("Updated Successfully")

# ====================================================
# OTHER PAGES SAME AS BEFORE
# ====================================================
