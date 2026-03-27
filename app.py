import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ---------------- PAGE CONFIG ----------------
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
product TEXT,
quantity INTEGER,
rate REAL,
gst REAL,
total REAL,
date TEXT)
""")

conn.commit()

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Settings")

page = st.sidebar.radio("Navigation", [
    "Create Invoice",
    "Invoice History",
    "Customer Master",
    "Product Master"
])

# -------- COMPANY SETTINGS --------
st.sidebar.subheader("🏢 Company Details")

company = st.sidebar.text_input("Company Name", "SHIVKRUTI ENTERPRISES")
address = st.sidebar.text_area("Address")
gst = st.sidebar.text_input("GSTIN")

logo_file = st.sidebar.file_uploader("Upload Logo", type=["png", "jpg", "jpeg"])

# ---------------- PDF FUNCTION ----------------
def generate_pdf(company, address, gst, logo_file,
                 invoice_no, invoice_date,
                 customer, contact, gstin,
                 items, subtotal, gst_amt, total):

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # LOGO
    if logo_file:
        elements.append(Image(logo_file, width=80, height=80))

    elements.append(Paragraph(f"<b>{company}</b>", styles["Title"]))
    elements.append(Paragraph(address, styles["Normal"]))
    elements.append(Paragraph(f"GSTIN: {gst}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Invoice No: {invoice_no}", styles["Normal"]))
    elements.append(Paragraph(f"Date: {invoice_date}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Bill To:</b> {customer}", styles["Normal"]))
    elements.append(Paragraph(f"Contact: {contact}", styles["Normal"]))
    elements.append(Paragraph(f"GSTIN: {gstin}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    table_data = [["Item", "Qty", "Rate", "Amount"]]

    for item, qty, rate in items:
        table_data.append([item, qty, rate, qty * rate])

    table_data.append(["", "", "Subtotal", subtotal])
    table_data.append(["", "", "GST (18%)", gst_amt])
    table_data.append(["", "", "Total", total])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return buffer

# ====================================================
# CREATE INVOICE
# ====================================================
if page == "Create Invoice":

    st.title("🧾 GST Invoice Generator")

    # Auto Invoice Number
    cursor.execute("SELECT MAX(invoice_no) FROM invoices")
    result = cursor.fetchone()
    invoice_no = 1001 if result[0] is None else result[0] + 1

    st.subheader(f"Invoice No: {invoice_no}")

    # Customer
    customers = pd.read_sql("SELECT * FROM customers", conn)

    if not customers.empty:
        customer_name = st.selectbox("Customer", customers["name"])
        cust = customers[customers["name"] == customer_name].iloc[0]
        contact = cust["contact"]
        gstin = cust["gstin"]
    else:
        customer_name = st.text_input("Customer Name")
        contact = st.text_input("Contact")
        gstin = st.text_input("GSTIN")

    invoice_date = st.date_input("Invoice Date", date.today())

    # Products
    products = pd.read_sql("SELECT * FROM products", conn)

    items = []
    rows = st.number_input("Number of Items", 1, 10, 1)

    for i in range(int(rows)):
        col1, col2, col3 = st.columns(3)

        with col1:
            if not products.empty:
                product = st.selectbox(f"Product {i+1}", products["name"], key=i)
                price = products[products["name"] == product]["price"].values[0]
            else:
                product = st.text_input(f"Product {i+1}")
                price = st.number_input(f"Rate {i+1}", key=f"rate{i}")

        with col2:
            qty = st.number_input(f"Qty {i+1}", 1)

        with col3:
            st.write(f"Price: ₹ {price}")

        items.append((product, qty, price))

    # Calculation
    subtotal = sum(q * p for _, q, p in items)
    gst_amt = subtotal * 0.18
    total = subtotal + gst_amt

    st.write("Subtotal:", subtotal)
    st.write("GST (18%):", gst_amt)
    st.write("Total:", total)

    # SAVE + GENERATE
    if st.button("Generate Invoice"):

        for item, qty, rate in items:
            cursor.execute("""
            INSERT INTO invoices
            (invoice_no, customer, product, quantity, rate, gst, total, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_no, customer_name, item, qty, rate, gst_amt, total, str(invoice_date)))

        conn.commit()

        pdf = generate_pdf(
            company, address, gst, logo_file,
            invoice_no, invoice_date,
            customer_name, contact, gstin,
            items, subtotal, gst_amt, total
        )

        st.success("Invoice Created Successfully ✅")

        st.download_button(
            label="Download PDF",
            data=pdf,
            file_name=f"invoice_{invoice_no}.pdf",
            mime="application/pdf"
        )

# ====================================================
# CUSTOMER MASTER
# ====================================================
elif page == "Customer Master":

    st.title("Customer Master")

    name = st.text_input("Customer Name")
    contact = st.text_input("Contact")
    gstin = st.text_input("GSTIN")

    if st.button("Add Customer"):
        cursor.execute(
            "INSERT INTO customers (name,contact,gstin) VALUES (?,?,?)",
            (name, contact, gstin)
        )
        conn.commit()
        st.success("Customer Added")

    df = pd.read_sql("SELECT * FROM customers", conn)
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
            (name, price)
        )
        conn.commit()
        st.success("Product Added")

    df = pd.read_sql("SELECT * FROM products", conn)
    st.dataframe(df)

# ====================================================
# INVOICE HISTORY
# ====================================================
elif page == "Invoice History":

    st.title("Invoice History")

    df = pd.read_sql("SELECT * FROM invoices", conn)
    st.dataframe(df)

    delete_id = st.number_input("Invoice No to Delete")

    if st.button("Delete Invoice"):
        cursor.execute("DELETE FROM invoices WHERE invoice_no=?", (delete_id,))
        conn.commit()
        st.success("Invoice Deleted")
