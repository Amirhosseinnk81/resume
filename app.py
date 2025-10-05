import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
from datetime import datetime

# بارگذاری متغیرهای محیطی
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
from models import db, Project,About, Skill, Experience, Education


# ایمیل
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

# کلاس امن برای پنل ادمین
class SecureModelView(ModelView):
    def is_accessible(self):
        return session.get('admin_authenticated', False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))
    
# پنل ادمین
admin = Admin(app, name='پنل مدیریت', template_mode='bootstrap4')
admin.add_view(SecureModelView(Project, db.session))
admin.add_view(SecureModelView(About, db.session))
admin.add_view(SecureModelView(Skill, db.session))
admin.add_view(SecureModelView(Experience, db.session))
admin.add_view(SecureModelView(Education, db.session))

# صفحه ورود ادمین
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == os.environ.get('ADMIN_USERNAME') and password == os.environ.get('ADMIN_PASSWORD'):
            session['admin_authenticated'] = True
            return redirect('/admin')
        flash('نام کاربری یا رمز عبور اشتباه است', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/')


# داده‌های دوزبانه
translations = {
"fa": {
"SITE_TITLE": "رزومهٔ من",
"NAME": "امیرحسین نعیمائی",
"TAGLINE": "توسعه‌دهندهٔ بک‌اند | Flask | Python",
"MENU_PROJECTS": "پروژه‌ها",
"MENU_ABOUT": "درباره‌من",
"MENU_CONTACT": "تماس",
"BTN_RESUME": "دانلود رزومه",
"BTN_PROJECTS": "مشاهدهٔ پروژه‌ها",
"CONTACT_TITLE": "تماس با من",
"CONTACT_NAME": "اسم",
"CONTACT_EMAIL": "ایمیل",
"CONTACT_MSG": "پیام",
"CONTACT_SEND": "ارسال",
"CONTACT_CLEAR": "پاک کردن",
"MSG_SUCCESS": "پیام شما با موفقیت ارسال شد!",
"MSG_ERROR": "لطفاً همهٔ فیلدها را پر کنید.",
"LOCATION" : "نوشهر",
},
"en": {
"SITE_TITLE": "My Resume",
"NAME": "Amirhossein Naeimaei",
"TAGLINE": "Backend Developer | Flask | Python",
"MENU_PROJECTS": "Projects",
"MENU_ABOUT": "About",
"MENU_CONTACT": "Contact",
"BTN_RESUME": "Download Resume",
"BTN_PROJECTS": "See Projects",
"CONTACT_TITLE": "Contact Me",
"CONTACT_NAME": "name",
"CONTACT_EMAIL": "E-mail",
"CONTACT_MSG": "Message",
"CONTACT_SEND": "Send",
"CONTACT_CLEAR": "Clear",
"MSG_SUCCESS": "Your message has been sent successfully!",
"MSG_ERROR": "Please fill in all fields.",
"LOCATION" : "Nowshahr",
}
}


# تنظیمات عمومی
SITE_TITLE = "رزومهٔ من"
SOCIALS = {
    "github": "https://github.com/Amirhosseinnk81",
    "linkedin": "https://www.linkedin.com/in/yourname/",
    "twitter": "https://x.com/Amirnk_81",
}
SOCIALS = {
    "github": "https://github.com/Amirhosseinnk81",
    "linkedin": "https://www.linkedin.com/in/yourname/",
    "twitter": "https://x.com/Amirnk_81",
}

@app.before_request
def set_lang():
    if 'lang' not in session:
        session['lang'] = 'fa'

@app.context_processor
def inject_globals():
    lang = session.get('lang', 'fa')
    return dict(SITE_TITLE=SITE_TITLE, SOCIALS=SOCIALS, year=datetime.now().year, t=translations[lang], lang=lang)

@app.route("/lang/<code>")
def switch_lang(code):
    if code in translations:
        session['lang'] = code
    return redirect(request.referrer or url_for("home"))


@app.route("/")    
def home():
    projects = Project.query.all()
    abouts = About.query.all()
    skills = Skill.query.all()
    experiences = Experience.query.all()
    education_list = Education.query.all()

    return render_template("index.html", projects=projects, skills=skills, abouts=abouts, experiences=experiences, education_list=education_list)

@app.route("/projects")
def projects():
    projects = Project.query.all()

    return render_template("projects.html",projects=projects,)


@app.route("/about")
def about():
    abouts = Project.query.all()
    skills = Skill.query.all()
    experiences = Experience.query.all()
    education_list = Education.query.all()

    return render_template("about.html",skills=skills, abouts=abouts, experiences=experiences, education_list=education_list)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    abouts = Project.query.all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        
        if not name or not email or not message:
            flash("لطفاً همهٔ فیلدها را پر کنید.", "danger")
            return redirect(url_for("contact"))

        os.makedirs("data", exist_ok=True)
        with open("data/messages.csv", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()},{name},{email},{message}\n")

        try:
            msg = Message(subject=f"پیام جدید از {name}", recipients=["barokfinancial@gmail.com"], body=f"From: {name} <{email}>\n\n{message}")
            mail.send(msg)
        except Exception as e:
            print("Email error:", e)

        flash("پیام شما با موفقیت ارسال شد!", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html", abouts=abouts)

@app.route("/toggle-lang")
def toggle_lang():
    current = session.get("lang", "fa")
    session["lang"] = "en" if current == "fa" else "fa"
    return redirect(request.referrer or url_for("index"))

@app.route("/resume")
def download_resume():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "myresume.pdf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)