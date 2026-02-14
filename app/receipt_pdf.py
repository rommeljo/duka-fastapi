from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build_receipt_pdf(*, shop_name: str, receipt_no: str, customer_name: str, customer_email: str,
                      amount: float, status: str, sale_id: int, phone: str,
                      mpesa_receipt: str | None = None, transaction_date: datetime | None = None) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    y = h - 60
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, f"{shop_name} - Payment Receipt")
    y -= 30

    c.setFont("Helvetica", 11)
    lines = [
        ("Receipt No:", receipt_no),
        ("Date:", (transaction_date or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")),
        ("Customer:", customer_name),
        ("Email:", customer_email),
        ("Phone:", phone),
        ("Sale ID:", str(sale_id)),
        ("Amount:", f"KES {amount:,.2f}"),
        ("Status:", status),
    ]
    if mpesa_receipt:
        lines.insert(2, ("Mpesa Receipt:", mpesa_receipt))

    for k, v in lines:
        c.drawString(50, y, k)
        c.drawString(170, y, v)
        y -= 18

    y -= 10
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, "Thank you for shopping with us.")
    y -= 20

    c.showPage()
    c.save()
    return buf.getvalue()
