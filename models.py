from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# مدل پروژه
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # عنوان پروژه
    short_description = db.Column(db.String(500), nullable=True)  # توضیحات کوتاه
    full_description = db.Column(db.Text, nullable=True)  # توضیحات کامل
    demo_link = db.Column(db.String(500), nullable=True)  # لینک دمو یا GitHub
    image_url = db.Column(db.String(500), nullable=True)  # تصویر پروژه
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # تاریخ ساخت
    status = db.Column(db.String(20), default='فعال')  # وضعیت (فعال / غیرفعال)
    stack = db.Column(db.String(300), nullable=True)
    
    def __repr__(self):
        return f"<Project {self.title}>"

class About(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)               # نام کامل
    title = db.Column(db.String(150), nullable=False)              # عنوان یا موقعیت شغلی (مثلاً "توسعه‌دهنده بک‌اند")
    short_bio = db.Column(db.String(300))                          # توضیح کوتاه برای نمایش در هدر یا صفحه اصلی
    full_bio = db.Column(db.Text)                                  # توضیح کامل درباره خودت
    email = db.Column(db.String(120))                              # ایمیل تماس
    phone = db.Column(db.String(50))                               # شماره تماس (اختیاری)
    location = db.Column(db.String(120))                           # محل زندگی یا کار
    linkedin = db.Column(db.String(200))                           # لینک LinkedIn
    github = db.Column(db.String(200))                             # لینک GitHub
    photo = db.Column(db.String(200))                              # مسیر عکس پروفایل
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)   # تاریخ آخرین ویرایش
    
    def __repr__(self):
        return f"<Project {self.title}>"
    
class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # نام مهارت
    level = db.Column(db.Integer, nullable=False)  # سطح مهارت (0-100)

    def __repr__(self):
        return f"<Skill {self.name} - {self.level}%>"
    
class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(50), nullable=False)        # سال یا بازه زمانی
    role = db.Column(db.String(150), nullable=False)       # نقش / شغل
    company = db.Column(db.String(150), nullable=False)    # شرکت
    desc = db.Column(db.Text, nullable=True)              # توضیحات

    def __repr__(self):
        return f"<Experience {self.role} at {self.company}>"

# مدل تحصیلات
class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(50), nullable=False)       # سال یا بازه تحصیلی
    degree = db.Column(db.String(150), nullable=False)    # مدرک
    university = db.Column(db.String(150), nullable=False) # دانشگاه
    desc = db.Column(db.Text, nullable=True)             # توضیحات

    def __repr__(self):
        return f"<Education {self.degree} at {self.university}>"