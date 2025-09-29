# resume_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os


os.makedirs("static/files", exist_ok=True)
# اگر فونت فارسی محلی داری (مثلاً Vazirmatn.ttf)، مسیرش رو بذار.
# توجه: ReportLab پشتیبانی کامل shaping فارسی نداره، ولی اگر فونت ساده باشه،
# متن نمایش داده می‌شه (ممکنه حروف جدا شوند). برای خروجی فارسی دقیق‌تر از WeasyPrint استفاده کن.
FONT_PATH = os.path.join(os.path.dirname(__file__), "static", "fonts", "Vazirmatn-Regular.ttf")
FONT_NAME = "Vazirmatn"

def register_font():
    if os.path.exists(FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
            return FONT_NAME
        except Exception:
            return "Helvetica"
    return "Helvetica"

def generate_resume(profile, experiences, education, skills, filename="static/files/resume.pdf"):
    # اطمینان از وجود مسیر خروجی
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    font_name = register_font()

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    margin_x = 20 * mm
    x = margin_x
    y = height - 30 * mm

    # هدر: نام و شغل
    c.setFont(font_name, 20)
    c.drawString(x, y, profile.get("name", ""))
    c.setFont(font_name, 12)
    c.drawString(x, y - 8 * mm, profile.get("job", ""))

    # اطلاعات تماس
    info_y = y - 16 * mm
    c.setFont(font_name, 10)
    c.drawString(x, info_y, f"✉️ {profile.get('email','')}")
    c.drawString(x + 80 * mm, info_y, f"📍 {profile.get('location','')}")

    # خط جداکننده
    c.line(margin_x, info_y - 6 * mm, width - margin_x, info_y - 6 * mm)

    cur_y = info_y - 14 * mm

    # بخش تجربه کاری
    c.setFont(font_name, 14)
    c.drawString(x, cur_y, "تجربیات کاری:")
    cur_y -= 8 * mm
    c.setFont(font_name, 11)
    for e in experiences:
        if cur_y < 40 * mm:
            c.showPage()
            cur_y = height - 30 * mm
            c.setFont(font_name, 11)
        role_line = f"{e.get('year','')} — {e.get('role','')} @ {e.get('company','')}"
        c.drawString(x + 5 * mm, cur_y, role_line)
        cur_y -= 6 * mm
        desc = e.get('desc','')
        # اگر توضیح خیلی طولانی بود، بشکن به خطوط کوچک‌تر
        max_chars = 80
        while desc:
            part = desc[:max_chars]
            c.drawString(x + 10 * mm, cur_y, part)
            desc = desc[max_chars:]
            cur_y -= 6 * mm
        cur_y -= 4 * mm

    # بخش تحصیلات
    c.setFont(font_name, 14)
    if cur_y < 60 * mm:
        c.showPage()
        cur_y = height - 30 * mm
    c.drawString(x, cur_y, "تحصیلات:")
    cur_y -= 8 * mm
    c.setFont(font_name, 11)
    for ed in education:
        ed_line = f"{ed.get('year','')} — {ed.get('degree','')} @ {ed.get('university','')}"
        c.drawString(x + 5 * mm, cur_y, ed_line)
        cur_y -= 8 * mm
        desc = ed.get('desc','')
        if desc:
            c.drawString(x + 10 * mm, cur_y, desc)
            cur_y -= 8 * mm

    # صفحه جدید برای مهارت‌ها (اگر جایی کم باشه)
    if cur_y < 60 * mm:
        c.showPage()
        cur_y = height - 30 * mm

    c.setFont(font_name, 14)
    c.drawString(x, cur_y, "مهارت‌ها:")
    cur_y -= 8 * mm
    c.setFont(font_name, 11)
    for s in skills:
        name = s.get("name")
        level = s.get("level", 0)
        bar_x = x + 5 * mm
        bar_y = cur_y - 4 * mm
        bar_w = 120 * mm
        bar_h = 5 * mm
        # متن مهارت
        c.drawString(bar_x, cur_y, f"{name} ({level}%)")
        # رسم پروگرس ساده
        c.roundRect(bar_x, bar_y - bar_h - 2, bar_w, bar_h, 1 * mm, stroke=1, fill=0)
        fill_w = (level/100.0) * bar_w
        if fill_w > 0:
            c.setFillColorRGB(0.0, 0.34, 0.7)  # آبی
            c.rect(bar_x, bar_y - bar_h - 2, fill_w, bar_h, stroke=0, fill=1)
            c.setFillColorRGB(0,0,0)
        cur_y -= 14 * mm

    # ذخیره PDF
    c.save()
    return filename
