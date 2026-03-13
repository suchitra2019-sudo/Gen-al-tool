import streamlit as st
import pandas as pd
import sqlite3
import streamlit.components.v1 as components
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

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
[
"Create Invoice",
"Invoice History",
"Customer Master",
"Product Master"
]
)

# ====================================================
# INVOICE HTML TEMPLATE
# ====================================================

def generate_invoice_html(company, address, gst, invoice_no,
date, customer, contact, gstin,
items, subtotal, cgst, sgst, transport, total):

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

    html = f"""

    <style>

    body {{
    font-family: Arial;
    }}

    .invoice {{
    width:800px;
    margin:auto;
    padding:20px;
    border:1px solid #ddd;
    }}

    table {{
    width:100%;
    border-collapse:collapse;
    }}

    th,td {{
    border:1px solid #ccc;
    padding:8px;
    text-align:left;
    }}

    .total {{
    font-weight:bold;
    }}

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

    <tr class="total">
    <td colspan="3">Subtotal</td>
    <td>{subtotal}</td>
    </tr>

    <tr class="total">
    <td colspan="3">CGST</td>
    <td>{cgst}</td>
    </tr>

    <tr class="total">
    <td colspan="3">SGST</td>
    <td>{sgst}</td>
    </tr>

    <tr class="total">
    <td colspan="3">Transport</td>
    <td>{transport}</td>
    </tr>

    <tr class="total">
    <td colspan="3">Grand Total</td>
    <td>{total}</td>
    </tr>

    </table>

    <br>

    <button onclick="window.print()">Print Invoice</button>

    </div>

    """

    return html


# ====================================================
# CREATE INVOICE
# ====================================================

if page == "Create Invoice":

    st.title("GST Invoice Generator")

    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()

    invoice_no = 1001 if result[0] is None else result[0] + 1

    st.subheader(f"Invoice No : {invoice_no}")

    # Company

    st.sidebar.header("Company")

    company = st.sidebar.text_input("Company Name","My Company")

    address = st.sidebar.text_area("Address","Mumbai")

    gst = st.sidebar.text_input("GSTIN","27ABCDE1234F1Z5")

    # Customer

    customers = pd.read_sql("SELECT * FROM customers",conn)

    if not customers.empty:

        customer_name = st.selectbox(
        "Select Customer",
        customers["name"]
        )

        cust = customers[customers["name"]==customer_name].iloc[0]

        contact = cust["contact"]
        gstin = cust["gstin"]

    else:

        customer_name = st.text_input("Customer")
        contact = st.text_input("Contact")
        gstin = st.text_input("GSTIN")

    invoice_date = st.date_input("Invoice Date", date.today())

    # Products

    st.subheader("Items")

    products = pd.read_sql("SELECT * FROM products",conn)

    items = []

    rows = st.number_input("Number of Items",1,10,1)

    for i in range(int(rows)):

        c1,c2,c3 = st.columns(3)

        with c1:

            if not products.empty:

                product = st.selectbox(
                f"Product {i+1}",
                products["name"],
                key=f"p{i}"
                )

                price = products[
                products["name"]==product
                ]["price"].values[0]

            else:

                product = st.text_input(f"Item {i+1}")
                price = st.number_input(f"Price {i+1}")

        with c2:
            qty = st.number_input(f"Qty {i+1}",1)

        with c3:
            st.write("Price :",price)

        items.append((product,qty,price))

    transport = st.number_input("Transport",0.0)

    # Calculation

    subtotal = sum(q*p for _,q,p in items)

    cgst = subtotal * 0.09
    sgst = subtotal * 0.09

    total = subtotal + cgst + sgst + transport

    st.write("Subtotal :",subtotal)
    st.write("CGST :",cgst)
    st.write("SGST :",sgst)
    st.write("Total :",total)

    # Preview

    st.subheader("Invoice Preview")

    if st.toggle("Show Preview"):

        html = generate_invoice_html(
        company,address,gst,invoice_no,
        invoice_date,customer_name,contact,gstin,
        items,subtotal,cgst,sgst,transport,total
        )

        components.html(html,height=900)

    # Save

    if st.button("Generate Invoice"):

        cursor.execute(
        "INSERT INTO invoices (invoice_no,customer,date,total) VALUES (?,?,?,?)",
        (invoice_no,customer_name,str(invoice_date),total)
        )

        conn.commit()

        st.success("Invoice Created")

# ====================================================
# CUSTOMER MASTER
# ====================================================

elif page == "Customer Master":

    st.title("Customer Master")

    name = st.text_input("Customer Name")
    contact = st.text_input("Contact")
    gst = st.text_input("GSTIN")

    if st.button("Add Customer"):

        cursor.execute(
        "INSERT INTO customers (name,contact,gstin) VALUES (?,?,?)",
        (name,contact,gst)
        )

        conn.commit()

        st.success("Customer Added")

    df = pd.read_sql("SELECT * FROM customers",conn)
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
        (name,price)
        )

        conn.commit()

        st.success("Product Added")

    df = pd.read_sql("SELECT * FROM products",conn)
    st.dataframe(df)

# ====================================================
# HISTORY
# ====================================================

elif page == "Invoice History":

    st.title("Invoice History")

    df = pd.read_sql("SELECT * FROM invoices",conn)

    st.dataframe(df)

    delete_id = st.number_input("Invoice Number to Delete")

    if st.button("Delete Invoice"):

        cursor.execute(
        "DELETE FROM invoices WHERE invoice_no=?",
        (delete_id,)
        )

        conn.commit()

        st.success("Invoice Deleted")
