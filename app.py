from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import io

def create_professional_invoice(
company_name,
company_address,
company_gstin,
invoice_no,
invoice_date,
customer_name,
customer_contact,
customer_gstin,
items,
subtotal,
cgst,
sgst,
transport,
grand_total,
logo_path=None
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    elements = []

# ------------------------------------------------
# HEADER SECTION
# ------------------------------------------------

    header_data=[]

    if logo_path:
        logo = Image(logo_path, width=80, height=50)
    else:
        logo = ""

    company_details = Paragraph(
        f"""
        <b>{company_name}</b><br/>
        {company_address}<br/>
        GSTIN : {company_gstin}
        """,
        styles['Normal']
    )

    header_data.append([logo, company_details])

    header_table = Table(header_data, colWidths=[100,400])

    elements.append(header_table)
    elements.append(Spacer(1,20))

# ------------------------------------------------
# INVOICE TITLE
# ------------------------------------------------

    title = Paragraph("<b>TAX INVOICE</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1,20))

# ------------------------------------------------
# BILLING DETAILS
# ------------------------------------------------

    billing_table = Table([
        ["Invoice No", invoice_no, "Invoice Date", invoice_date],
        ["Customer", customer_name, "Contact", customer_contact],
        ["Customer GSTIN", customer_gstin, "", ""]
    ], colWidths=[120,200,120,120])

    billing_table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.grey)
    ]))

    elements.append(billing_table)

    elements.append(Spacer(1,20))

# ------------------------------------------------
# PRODUCT TABLE
# ------------------------------------------------

    table_data=[["Item Description","Qty","Rate","Amount"]]

    for item,qty,price in items:
        table_data.append([item,qty,price,qty*price])

    table_data.append(["","","Subtotal",subtotal])
    table_data.append(["","","CGST (9%)",cgst])
    table_data.append(["","","SGST (9%)",sgst])
    table_data.append(["","","Transport",transport])
    table_data.append(["","","Grand Total",grand_total])

    product_table = Table(table_data, colWidths=[250,80,100,120])

    product_table.setStyle(TableStyle([

        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2E5090")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),

        ("GRID",(0,0),(-1,-1),1,colors.grey),

        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(2,-1),(3,-1),"Helvetica-Bold"),

        ("ALIGN",(1,1),(-1,-1),"CENTER")

    ]))

    elements.append(product_table)

    elements.append(Spacer(1,30))

# ------------------------------------------------
# FOOTER
# ------------------------------------------------

    footer = Table([
        ["Payment Terms : 15 Days", "", "Authorized Signature"],
        ["Bank : ABC Bank", "", ""],
        ["Account No : 1234567890", "", ""]
    ], colWidths=[250,150,150])

    footer.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.lightgrey)
    ]))

    elements.append(footer)

    doc.build(elements)

    buffer.seek(0)

    return buffer
