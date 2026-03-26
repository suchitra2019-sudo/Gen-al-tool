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

# Customers
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
contact TEXT,
gstin TEXT)
""")

# Products
cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
price REAL)
""")

# Invoices (UPDATED)
cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_no INTEGER,
customer TEXT,
date TEXT,
subtotal REAL,
gst REAL,
sgst REAL,
transport REAL,
total REAL)
""")

# Invoice Items (NEW)
cursor.execute("""
CREATE TABLE IF NOT EXISTS invoice_items(
id INTEGER PRIMARY KEY AUTOINCREMENT,
invoice_no INTEGER,
product TEXT,
qty INTEGER,
price REAL,
amount REAL)
""")

conn.commit()

# ---------------- SIDEBAR ----------------

st.sidebar.title("Billing Menu")

page = st.sidebar.radio(
"Navigation",
["Create Invoice", "Invoice History", "Customer Master", "Product Master"]
)

# ====================================================
# PDF GENERATOR (FIXED)
# ====================================================

def generate_pdf(company,address,gst,logo,
invoice_no,date,customer,contact,gstin,
items,subtotal,GST,sgst,transport,total):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    elements = []

    # Header
    if logo:
        logo_img = Image(logo, width=60, height=60)
    else:
        logo_img = Spacer(1,1)

    company_block = Paragraph(
        f"<b>{company}</b><br/>{address}<br/>GSTIN : {gst}",
        styles["Normal"]
    )

    elements.append(Table([[logo_img, company_block]]))
    elements.append(Spacer(1,20))

    # Items Table
    data=[["Item","Qty","Rate","Amount"]]
    for d,q,p in items:
        data.append([d,q,p,q*p])

    data.append(["","","Subtotal",subtotal])
    data.append(["","","GST",GST])
    data.append(["","","SGST",sgst])
    data.append(["","","Transport",transport])
    data.append(["","","Total",total])

    table=Table(data)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.grey)]))

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

    # Company
    company=st.text_input("Company Name","SHIVKRUTI ENTERPRISES")
    address=st.text_area("Address")
    gst=st.text_input("GSTIN")

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

    invoice_date=st.date_input("Date",date.today())

    # Products
    products=pd.read_sql("SELECT * FROM products",conn)

    items=[]
    rows=st.number_input("Items",1,10,1)

    for i in range(int(rows)):
        col1,col2,col3=st.columns(3)

        with col1:
            if not products.empty:
                product=st.selectbox(f"Product {i+1}",products["name"],key=i)
                price=products[products["name"]==product]["price"].values[0]
            else:
                product=st.text_input(f"Item {i+1}")
                price=st.number_input(f"Price {i+1}")

        with col2:
            qty=st.number_input(f"Qty {i+1}",1)

        with col3:
            st.write(price)

        items.append((product,qty,price))

    transport=st.number_input("Transport",0.0)

    subtotal=sum(q*p for _,q,p in items)
    GST=subtotal*0.09
    sgst=subtotal*0.09
    total=subtotal+GST+sgst+transport

    st.write("Total:",total)

    # SAVE
    if st.button("Generate Invoice"):

        # Save invoice
        cursor.execute("""
        INSERT INTO invoices 
        (invoice_no,customer,date,subtotal,gst,sgst,transport,total)
        VALUES (?,?,?,?,?,?,?,?)
        """,(invoice_no,customer_name,str(invoice_date),
             subtotal,GST,sgst,transport,total))

        # Save items
        for d,q,p in items:
            cursor.execute("""
            INSERT INTO invoice_items 
            (invoice_no,product,qty,price,amount)
            VALUES (?,?,?,?,?)
            """,(invoice_no,d,q,p,q*p))

        conn.commit()

        pdf=generate_pdf(company,address,gst,None,
        invoice_no,invoice_date,customer_name,contact,gstin,
        items,subtotal,GST,sgst,transport,total)

        st.success("Invoice Saved")

        st.download_button(
        "Download PDF",
        data=pdf,
        file_name=f"invoice_{invoice_no}.pdf"
        )

# ====================================================
# INVOICE HISTORY
# ====================================================

elif page=="Invoice History":

    st.title("Invoice History")

    df=pd.read_sql("SELECT * FROM invoices",conn)
    st.dataframe(df)

    inv=st.number_input("Enter Invoice No")

    if st.button("View Items"):
        items_df=pd.read_sql(
        f"SELECT * FROM invoice_items WHERE invoice_no={inv}",conn)
        st.dataframe(items_df)

# ====================================================
# CUSTOMER MASTER
# ====================================================

elif page=="Customer Master":

    name=st.text_input("Name")
    contact=st.text_input("Contact")
    gstin=st.text_input("GSTIN")

    if st.button("Add"):
        cursor.execute("INSERT INTO customers VALUES(NULL,?,?,?)",(name,contact,gstin))
        conn.commit()

# ====================================================
# PRODUCT MASTER
# ====================================================

elif page=="Product Master":

    name=st.text_input("Product")
    price=st.number_input("Price")

    if st.button("Add"):
        cursor.execute("INSERT INTO products VALUES(NULL,?,?)",(name,price))
        conn.commit()
