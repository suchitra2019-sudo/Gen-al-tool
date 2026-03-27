import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# ---------------- DATABASE ---------------- #
conn = sqlite3.connect("invoice.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT,
    customer_name TEXT,
    product TEXT,
    quantity INTEGER,
    rate REAL,
    gst REAL,
    total REAL,
    date TEXT
)
""")
conn.commit()

# ---------------- FUNCTIONS ---------------- #
def save_invoice(data):
    cursor.execute("""
    INSERT INTO invoices (
        invoice_no, customer_name, product,
        quantity, rate, gst, total, date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

def fetch_invoices():
    cursor.execute("SELECT * FROM invoices")
    return cursor.fetchall()

# ---------------- UI ---------------- #
st.set_page_config(page_title="GST Invoice Generator", layout="wide")

st.title("🧾 GST Invoice Generator")

# ---------------- INPUT SECTION ---------------- #
col1, col2 = st.columns(2)

with col1:
    customer_name = st.text_input("Customer Name")
    invoice_no = st.text_input("Invoice Number")
    product = st.text_input("Product (Woven Bags)")
    
with col2:
    quantity = st.number_input("Quantity", min_value=1, step=1)
    rate = st.number_input("Rate", min_value=0.0)
    gst_percent = st.selectbox("GST %", [5, 12, 18])

# ---------------- CALCULATION ---------------- #
subtotal = quantity * rate
gst_amount = subtotal * gst_percent / 100
total = subtotal + gst_amount

st.markdown("### 💰 Invoice Summary")
st.write(f"Subtotal: ₹ {subtotal}")
st.write(f"GST ({gst_percent}%): ₹ {gst_amount}")
st.write(f"Total: ₹ {total}")

# ---------------- SAVE BUTTON ---------------- #
if st.button("💾 Save Invoice"):
    if customer_name and invoice_no:
        data = (
            invoice_no,
            customer_name,
            product,
            quantity,
            rate,
            gst_percent,
            total,
            str(date.today())
        )
        save_invoice(data)
        st.success("Invoice Saved Successfully ✅")
    else:
        st.error("Please fill required fields ❌")

# ---------------- VIEW DATA ---------------- #
st.markdown("---")
st.subheader("📂 Saved Invoices")

data = fetch_invoices()

if data:
    df = pd.DataFrame(data, columns=[
        "ID", "Invoice No", "Customer", "Product",
        "Qty", "Rate", "GST %", "Total", "Date"
    ])
    st.dataframe(df, use_container_width=True)
else:
    st.info("No invoices found")
