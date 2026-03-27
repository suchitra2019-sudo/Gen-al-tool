import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date
import io

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

page = st.sidebar.radio(
"Navigation",
["Create Invoice","Invoice History","Customer Master","Product Master"]
)

# ====================================================
# PDF GENERATOR (FIXED)
# ====================================================

def generate_pdf(company,address,gst,logo,
invoice_no,date,customer,contact,gstin,
items,subtotal,cgst,sgst,transport,total):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    elements = []

    # LOGO FIX
    logo_img = ""
    if logo:
        logo_bytes = io.BytesIO(logo.read())
        logo_img = Image(logo_bytes, width=60, height=60)

    # HEADER
    header = Table([
        [logo_img, Paragraph(f"<b>{company}</b><br/>{address}<br/>GSTIN: {gst}", styles["Normal"])]
    ], colWidths=[80, 400])

    elements.append(header)
    elements.append(Spacer(1, 20))

    # TITLE
    elements.append(Paragraph(f"<b>INVOICE #{invoice_no}</b>", styles["Title"]))
    elements.append(Spacer(1, 20))

    # CUSTOMER
    elements.append(Paragraph(f"{customer}<br/>{contact}<br/>GSTIN: {gstin}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ITEMS
    data = [["Item","Qty","Rate","Amount"]]

    for desc,qty,price in items:
        data.append([desc,qty,price,qty*price])

    data += [
        ["","","Subtotal",subtotal],
        ["","","CGST 9%",cgst],
        ["","","SGST 9%",sgst],
        ["","","Transport",transport],
        ["","","Total",total]
    ]

    table = Table(data)

    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.lightblue)
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return buffer

# ====================================================
# CREATE INVOICE
# ====================================================

if page=="Create Invoice":

    st.title("GST Invoice Generator")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result=cursor.fetchone()
    invoice_no=1001 if result[0] is None else result[0]+1

    st.subheader(f"Invoice No : {invoice_no}")

    # COMPANY
    company=st.sidebar.text_input("Company Name","SHIVKRUTI ENTERPRISES")
    address=st.sidebar.text_area("Address")
    gst=st.sidebar.text_input("GSTIN")

    logo=st.sidebar.file_uploader("Logo")

    # CUSTOMER
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

    invoice_date=st.date_input("Date",date.today())

    # PRODUCTS
    products=pd.read_sql("SELECT * FROM products",conn)

    items=[]
    rows=st.number_input("Items",1,10,1)

    for i in range(int(rows)):

        col1,col2,col3=st.columns(3)

        with col1:
            if not products.empty:
                product=st.selectbox(f"Product {i}",products["name"],key=i)
                price=float(products[products["name"]==product]["price"].values[0])
            else:
                product=st.text_input(f"Item {i}")
                price=st.number_input(f"Price {i}",0.0)

        with col2:
            qty=st.number_input(f"Qty {i}",1)

        with col3:
            st.write(price)

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

    # SAVE + PDF
    if st.button("Generate Invoice"):

        try:
            cursor.execute(
            "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
            (invoice_no,customer_name,str(invoice_date),total)
            )
            conn.commit()

            pdf=generate_pdf(
            company,address,gst,logo,
            invoice_no,invoice_date,
            customer_name,contact,gstin,
            items,subtotal,cgst,sgst,transport,total
            )

            st.success("Invoice Created")

            st.download_button(
            "Download PDF",
            pdf,
            file_name=f"invoice_{invoice_no}.pdf"
            )

        except Exception as e:
            st.error(f"Error: {e}")

# ====================================================
# CUSTOMER MASTER
# ====================================================

elif page=="Customer Master":

    st.title("Customer Master")

    name=st.text_input("Name")
    contact=st.text_input("Contact")
    gstin=st.text_input("GSTIN")

    if st.button("Add"):
        cursor.execute(
        "INSERT INTO customers (name,contact,gstin) VALUES (?,?,?)",
        (name,contact,gstin)
        )
        conn.commit()
        st.success("Added")

    st.dataframe(pd.read_sql("SELECT * FROM customers",conn))

# ====================================================
# PRODUCT MASTER
# ====================================================

elif page=="Product Master":

    st.title("Product Master")

    name=st.text_input("Name")
    price=st.number_input("Price",0.0)

    if st.button("Add"):
        cursor.execute(
        "INSERT INTO products (name,price) VALUES (?,?)",
        (name,price)
        )
        conn.commit()
        st.success("Added")

    st.dataframe(pd.read_sql("SELECT * FROM products",conn))

# ====================================================
# HISTORY
# ====================================================

elif page=="Invoice History":

    st.title("Invoice History")

    df=pd.read_sql("SELECT * FROM invoices",conn)
    st.dataframe(df)

    delete_id=st.number_input("Invoice No")

    if st.button("Delete"):
        cursor.execute("DELETE FROM invoices WHERE invoice_no=?", (delete_id,))
        conn.commit()
        st.success("Deleted")
