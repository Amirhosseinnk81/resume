import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-in-production")

# داده‌های دوزبانه
translations = {
"fa": {
"SITE_TITLE": "رزومهٔ من",
"NAME": "نام شما",
"TAGLINE": "توسعه‌دهندهٔ بک‌اند | Flask | Python",
"MENU_PROJECTS": "پروژه‌ها",
"MENU_ABOUT": "درباره‌من",
"MENU_CONTACT": "تماس",
"BTN_RESUME": "دانلود رزومه",
"BTN_PROJECTS": "مشاهدهٔ پروژه‌ها",
"CONTACT_TITLE": "تماس با من",
"CONTACT_NAME": "نام",
"CONTACT_EMAIL": "ایمیل",
"CONTACT_MSG": "پیام",
"CONTACT_SEND": "ارسال",
"CONTACT_CLEAR": "پاک کردن",
"MSG_SUCCESS": "پیام شما با موفقیت ارسال شد!",
"MSG_ERROR": "لطفاً همهٔ فیلدها را پر کنید.",
},
"en": {
"SITE_TITLE": "My Resume",
"NAME": "Your Name",
"TAGLINE": "Backend Developer | Flask | Python",
"MENU_PROJECTS": "Projects",
"MENU_ABOUT": "About",
"MENU_CONTACT": "Contact",
"BTN_RESUME": "Download Resume",
"BTN_PROJECTS": "See Projects",
"CONTACT_TITLE": "Contact Me",
"CONTACT_NAME": "Name",
"CONTACT_EMAIL": "Email",
"CONTACT_MSG": "Message",
"CONTACT_SEND": "Send",
"CONTACT_CLEAR": "Clear",
"MSG_SUCCESS": "Your message has been sent successfully!",
"MSG_ERROR": "Please fill in all fields.",
}
}

# تنظیمات ساده
SITE_TITLE = "رزومهٔ من"
NAME = "نام شما"
TAGLINE = "توسعه‌دهندهٔ بک‌اند | Flask | Python"
SOCIALS = {
    "github": "https://github.com/yourname",
    "linkedin": "https://www.linkedin.com/in/yourname/",
    "twitter": "https://x.com/yourname",
}
SKILLS = [
{"name": "Python", "level": 65},
{"name": "Flask", "level": 35},
{"name": "JavaScript", "level": 10},
{"name": "HTML/CSS", "level": 50}
]
PROJECTS = [
{
"title": "سامانهٔ رزرو هتل",
"desc": "یک وب‌اپ با Flask و PostgreSQL برای مدیریت رزروها.",
"stack": ["Flask", "PostgreSQL", "Bootstrap"],
"link": "https://example.com/project1"
},
{
"title": "داشبورد مانیتورینگ شبکه",
"desc": "نمایش وضعیت دستگاه‌ها و ترافیک با چارت‌های زنده.",
"stack": ["FastAPI", "Redis", "WebSocket"],
"link": "https://example.com/project2"
}
]

EXPERIENCES = [
{
"year": "2023 - حالا",
"role": "توسعه‌دهندهٔ بک‌اند",
"company": "شرکت فناوری ایکس",
"desc": "توسعه و نگهداری سرویس‌های میکروسرویسی با Flask و Docker"
},
{
"year": "2020 - 2023",
"role": "کارشناس شبکه و IT",
"company": "هتل Y",
"desc": "مدیریت شبکه، CCTV و سیستم‌های تلفنی"
}
]


EDUCATION = [
{
"year": "2016 - 2020",
"degree": "کارشناسی مهندسی کامپیوتر",
"university": "دانشگاه مثال",
"desc": "گرایش نرم‌افزار، پروژه پایانی در زمینهٔ یادگیری ماشین"
}
]

@app.before_request
def set_lang():
    if 'lang' not in session:
        session['lang'] = 'fa' # پیش‌فرض فارسی

@app.context_processor
def inject_globals():
    lang = session.get('lang', 'fa')
    return dict(
        SITE_TITLE=SITE_TITLE,
        NAME=NAME,
        TAGLINE=TAGLINE,
        SOCIALS=SOCIALS,
        year=datetime.now().year,
        t=translations[lang],
        lang=lang,
)
    
    
    
@app.route("/lang/<code>")
def switch_lang(code):
    if code in translations:
        session['lang'] = code
    return redirect(request.referrer or url_for("home"))

@app.route("/")    
def home():
    return render_template("index.html", skills=SKILLS, projects=PROJECTS)

@app.route("/projects")
def projects():
    return render_template("projects.html", projects=PROJECTS)


@app.route("/about")
def about():
    return render_template("about.html", experiences=EXPERIENCES, education=EDUCATION, skills=SKILLS)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("لطفاً همهٔ فیلدها را پر کنید.", "danger")
            return redirect(url_for("contact"))
        # ذخیرهٔ سادهٔ پیام‌ها در یک فایل CSV (قابل جایگزینی با ایمیل/دیتابیس)
        os.makedirs("data", exist_ok=True)
        with open("data/messages.csv", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()},{name},{email},{message}\n")
        flash("پیام شما با موفقیت ارسال شد!", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route('/download/resume')
def download_resume():
    # فایل resume.pdf را داخل static/files قرار دهید
    directory = os.path.join(app.root_path, 'static', 'files')
    return send_from_directory(directory, 'resume.pdf', as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)