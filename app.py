import streamlit as st
import pandas as pd
import io
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import date

st.set_page_config(page_title="Professional Invoice Generator", layout="wide")

st.title("🧾 Professional GST Invoice Generator")

# ---------------- COMPANY INFO ----------------

with st.sidebar:
    st.header("Company Details")

    company = st.text_input("Company Name","ABC Technologies")
    address = st.text_area("Company Address","Mumbai, India")
    gst = st.text_input("Company GSTIN","27ABCDE1234F1Z5")
    logo = st.file_uploader("Upload Company Logo", type=["png","jpg","jpeg"])


# ---------------- CUSTOMER DETAILS ----------------

st.subheader("Customer Details")

col1,col2,col3 = st.columns(3)

with col1:
    invoice_no = st.text_input("Invoice Number","INV-001")

with col2:
    invoice_date = st.date_input("Invoice Date",date.today())

with col3:
    customer = st.text_input("Customer Name")

contact = st.text_input("Customer Contact")
gstin = st.text_input("Customer GSTIN")

# ---------------- ITEMS ----------------

st.subheader("Invoice Items")

if "items" not in st.session_state:
    st.session_state.items = []

col1,col2,col3,col4 = st.columns(4)

with col1:
    item = st.text_input("Item Description")

with col2:
    qty = st.number_input("Qty",1)

with col3:
    rate = st.number_input("Rate",0.0)

with col4:
    if st.button("Add Item"):
        st.session_state.items.append([item,qty,rate])

items_df = pd.DataFrame(st.session_state.items, columns=["Description","Qty","Rate"])

st.dataframe(items_df,use_container_width=True)

# ---------------- CALCULATIONS ----------------

subtotal = sum(q*r for _,q,r in st.session_state.items)

cgst = subtotal * 0.09
sgst = subtotal * 0.09

transport = st.number_input("Transport Charges",0.0)

total = subtotal + cgst + sgst + transport

st.markdown(f"### Subtotal: ₹{subtotal}")
st.markdown(f"### CGST (9%): ₹{cgst}")
st.markdown(f"### SGST (9%): ₹{sgst}")
st.markdown(f"### Grand Total: ₹{total}")

# ---------------- PDF FUNCTION ----------------

def generate_pdf():

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer,pagesize=A4)

    styles = getSampleStyleSheet()
    elements = []

# HEADER

    header = []

    if logo:
        logo_img = Image(logo, width=80, height=60)
    else:
        logo_img = ""

    company_info = Paragraph(
        f"<b>{company}</b><br/>{address}<br/>GSTIN : {gst}",
        styles["Normal"]
    )

    header.append([logo_img, company_info])

    header_table = Table(header, colWidths=[100,400])

    elements.append(header_table)
    elements.append(Spacer(1,20))

# TITLE

    title = Table([["TAX INVOICE"]], colWidths=[500])

    title.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0),colors.HexColor("#2F5597")),
        ("TEXTCOLOR",(0,0),(0,0),colors.white),
        ("ALIGN",(0,0),(0,0),"CENTER"),
        ("FONTSIZE",(0,0),(0,0),16)
    ]))

    elements.append(title)
    elements.append(Spacer(1,20))

# CUSTOMER TABLE

    info = Table([

        ["Invoice No",invoice_no,"Date",str(invoice_date)],
        ["Customer",customer,"Contact",contact],
        ["GSTIN",gstin,"",""]

    ],colWidths=[120,180,120,180])

    info.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.lightgrey),
        ("BACKGROUND",(0,0),(0,-1),colors.whitesmoke)
    ]))

    elements.append(info)
    elements.append(Spacer(1,20))

# ITEM TABLE

    data=[["Item","Qty","Rate","Amount"]]

    for desc,qty,rate in st.session_state.items:
        data.append([desc,qty,rate,qty*rate])

    data.append(["","","Subtotal",subtotal])
    data.append(["","","CGST (9%)",cgst])
    data.append(["","","SGST (9%)",sgst])
    data.append(["","","Transport",transport])
    data.append(["","","Total",total])

    table = Table(data, colWidths=[240,80,100,120])

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2F5597")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.grey),
        ("ALIGN",(1,1),(-1,-1),"CENTER")
    ]))

    elements.append(table)

# FOOTER (NO TABLE FORMAT)

    elements.append(Spacer(1,40))

    elements.append(Paragraph("Payment Terms: Due within 15 days",styles["Normal"]))
    elements.append(Paragraph("Bank: ABC Bank",styles["Normal"]))
    elements.append(Paragraph("Account No: 1234567890",styles["Normal"]))

    elements.append(Spacer(1,30))

    elements.append(Paragraph("<b>Authorized Signature</b>",styles["Normal"]))

# BUILD PDF

    doc.build(elements)

    buffer.seek(0)

    return buffer

# ---------------- PREVIEW ----------------

if st.button("Preview Invoice"):

    st.subheader("Invoice Preview")

    preview_df = items_df.copy()

    preview_df["Amount"] = preview_df["Qty"] * preview_df["Rate"]

    st.table(preview_df)

# ---------------- DOWNLOAD PDF ----------------

if st.button("Generate Invoice PDF"):

    pdf = generate_pdf()

    st.download_button(
        label="Download Invoice PDF",
        data=pdf,
        file_name="invoice.pdf",
        mime="application/pdf"
    )
