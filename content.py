"""
Static site content: profile, translations, experience, education.

Previously these lived as module-level constants in app.py, mixed in with
route definitions and app wiring. They are content, not application code, so
they are isolated here.

EXPERIENCES and EDUCATION gained a `stack` list: every reference portfolio
reviewed tags each role with the technologies used in it, which is both what
a reader scans for and what makes the page findable by keyword. The previous
free-text `desc` alone carried none of that signal.
"""

PROFILE = {
    "name": "امیرحسین نعیمائی",
    "name_en": "Amirhossein Naeimaei",
    "job": "توسعه‌دهنده بک‌اند (Python/Flask)",
    "job_en": "Backend Developer (Python/Flask)",
    "location": "مازندران، ایران",
    "location_en": "Mazandaran, Iran",
    "email": "amirhossein.naimaei81@gmail.com",
}

SITE_TITLE = "رزومهٔ من"
NAME = "امیرحسین نعیمائی"
TAGLINE = "توسعه‌دهندهٔ بک‌اند | Flask | Python"
LOCATION = "نوشهر"
CONTACT_EMAIL = "amirhossein.naimaei81@gmail.com"


TRANSLATIONS = {
    "fa": {
        "SITE_TITLE": "رزومهٔ من",
        "NAME": "امیرحسین نعیمائی",
        "TAGLINE": "توسعه‌دهندهٔ بک‌اند | Flask | Python",
        "META_DESCRIPTION": (
            "رزومه و نمونه‌کارهای امیرحسین نعیمائی، توسعه‌دهندهٔ بک‌اند "
            "پایتون با تمرکز بر Flask، طراحی API و پایگاه داده."
        ),
        "MENU_HOME": "خانه",
        "MENU_PROJECTS": "پروژه‌ها",
        "MENU_ABOUT": "درباره‌من",
        "MENU_ARTICLES": "مقالات",
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
        "LOCATION": "نوشهر",
        "SKILLS_TITLE": "مهارت‌ها",
        "VIEWS": "بازدید",
        "EXPERIENCE_TITLE": "تجربهٔ کاری",
        "EDUCATION_TITLE": "تحصیلات",
        "ERR_404_TITLE": "صفحه پیدا نشد",
        "ERR_404_BODY": "آدرسی که دنبالش بودید وجود ندارد یا جابه‌جا شده است.",
        "ERR_500_TITLE": "خطای سرور",
        "ERR_500_BODY": "مشکلی از سمت ما پیش آمد. لطفاً بعداً دوباره تلاش کنید.",
        "ERR_HOME": "بازگشت به خانه",
        "SKILL_CAT_LANGUAGES": "زبان‌ها",
        "SKILL_CAT_FRAMEWORKS": "فریم‌ورک‌ها",
        "SKILL_CAT_DATABASES": "پایگاه داده",
        "SKILL_CAT_TOOLS": "ابزارها",
    },
    "en": {
        "SITE_TITLE": "My Resume",
        "NAME": "Amirhossein Naeimaei",
        "TAGLINE": "Backend Developer | Flask | Python",
        "META_DESCRIPTION": (
            "Resume and portfolio of Amirhossein Naeimaei, a Python backend "
            "developer focused on Flask, API design and databases."
        ),
        "MENU_HOME": "Home",
        "MENU_PROJECTS": "Projects",
        "MENU_ABOUT": "About",
        "MENU_ARTICLES": "Articles",
        "MENU_CONTACT": "Contact",
        "BTN_RESUME": "Download Resume",
        "BTN_PROJECTS": "See Projects",
        "CONTACT_TITLE": "Contact Me",
        "CONTACT_NAME": "Name",
        "CONTACT_EMAIL": "E-mail",
        "CONTACT_MSG": "Message",
        "CONTACT_SEND": "Send",
        "CONTACT_CLEAR": "Clear",
        "MSG_SUCCESS": "Your message has been sent successfully!",
        "MSG_ERROR": "Please fill in all fields.",
        "LOCATION": "Nowshahr",
        "SKILLS_TITLE": "Skills",
        "VIEWS": "views",
        "EXPERIENCE_TITLE": "Experience",
        "EDUCATION_TITLE": "Education",
        "ERR_404_TITLE": "Page not found",
        "ERR_404_BODY": "The page you were looking for does not exist or has moved.",
        "ERR_500_TITLE": "Server error",
        "ERR_500_BODY": "Something went wrong on our side. Please try again later.",
        "ERR_HOME": "Back to home",
        "SKILL_CAT_LANGUAGES": "Languages",
        "SKILL_CAT_FRAMEWORKS": "Frameworks",
        "SKILL_CAT_DATABASES": "Databases",
        "SKILL_CAT_TOOLS": "Tools",
    },
}

DEFAULT_LANG = "fa"


EXPERIENCES = [
    {
        "year": "2021 - حالا",
        "year_en": "2021 - Present",
        "role": "توسعه‌دهندهٔ بک‌اند",
        "role_en": "Backend Developer",
        "company": "فریلنسر",
        "company_en": "Freelance",
        "desc": "توسعه و نگهداری سرویس‌های میکروسرویسی با Flask و Docker",
        "desc_en": "Building and maintaining microservices with Flask and Docker.",
        "stack": ["Python", "Flask", "Docker", "PostgreSQL", "Git"],
    },
    {
        "year": "2023 - حالا",
        "year_en": "2023 - Present",
        "role": "کارشناس شبکه و IT",
        "role_en": "Network & IT Specialist",
        "company": "هتل آراز",
        "company_en": "Araz Hotel",
        "desc": "مدیریت شبکه، CCTV و سیستم‌های تلفنی",
        "desc_en": "Managing networking, CCTV and telephony systems.",
        "stack": ["Linux", "Networking", "CCTV", "VoIP", "Windows Server"],
    },
]


EDUCATION = [
    {
        "year": "2018 - 2021",
        "degree": "دیپلم ریاضی و فیزیک",
        "degree_en": "High School Diploma, Mathematics & Physics",
        "university": "مدرسه شهید مدرس",
        "university_en": "Shahid Modarres High School",
        "desc": "تحصیل در رشته ریاضی و فیزیک",
        "desc_en": "Mathematics and physics track.",
    },
    {
        "year": "2021 - 2023",
        "degree": "فوق دیپلم نرم‌افزار",
        "degree_en": "Associate Degree, Software Engineering",
        "university": "دانشگاه آزاد اسلامی واحد چالوس",
        "university_en": "Islamic Azad University, Chalus Branch",
        "desc": "گرایش نرم‌افزار و برنامه‌نویسی",
        "desc_en": "Software and programming specialisation.",
    },
    {
        "year": "2023 - 2025",
        "degree": "کارشناسی مهندسی کامپیوتر",
        "degree_en": "B.Sc. Computer Engineering",
        "university": "دانشگاه آزاد اسلامی واحد چالوس",
        "university_en": "Islamic Azad University, Chalus Branch",
        "desc": "گرایش نرم‌افزار، پروژه پایانی در زمینهٔ یادگیری ماشین",
        "desc_en": "Software specialisation; final project on machine learning.",
    },
    {
        "year": "2025 - حالا",
        "year_en": "2025 - Present",
        "degree": "کارشناسی ارشد مدیریت سیستم‌های اطلاعاتی",
        "degree_en": "M.Sc. Information Systems Management",
        "university": "دانشگاه مارلیک نوشهر",
        "university_en": "Marlik University, Nowshahr",
        "desc": "در حال حاضر دانشجو، تمرکز بر مدیریت سیستم‌ها و تحلیل داده‌ها",
        "desc_en": "In progress; focused on systems management and data analysis.",
    },
]


# Shown in the footer the way brittanychiang.com credits its own stack —
# for a backend developer the site's own architecture is part of the pitch.
BUILT_WITH = ["Python", "Flask", "SQLAlchemy", "Jinja2", "Bootstrap", "Docker"]


SKILL_ICON_MAP = {
    "python": ("python", "3776AB"),
    "flask": ("flask", "64748b"),
    "javascript": ("javascript", "F7DF1E"),
    "js": ("javascript", "F7DF1E"),
    "django": ("django", "092E20"),
    "git": ("git", "F05032"),
    "git&github": ("git", "F05032"),
    "github": ("github", "181717"),
    "html": ("html5", "E34F26"),
    "html/css": ("html5", "E34F26"),
    "css": ("css3", "1572B6"),
    "sql": ("mysql", "4479A1"),
    "mysql": ("mysql", "4479A1"),
    "postgresql": ("postgresql", "4169E1"),
    "sqlite": ("sqlite", "003B57"),
    "sqlalchemy": ("sqlalchemy", "D71F00"),
    "docker": ("docker", "2496ED"),
    "react": ("react", "61DAFB"),
    "vue": ("vuedotjs", "4FC08D"),
    "linux": ("linux", "FCC624"),
    "nginx": ("nginx", "009639"),
    "redis": ("redis", "DC382D"),
    "typescript": ("typescript", "3178C6"),
    "bootstrap": ("bootstrap", "7952B3"),
    "tailwind": ("tailwindcss", "06B6D4"),
    "jinja2": ("jinja", "B41717"),
    "networking": ("cisco", "1BA0D7"),
    "voip": ("asterisk", "F60026"),
}


def get_skill_icon(name):
    icon, color = SKILL_ICON_MAP.get((name or "").strip().lower(), (None, "2563eb"))
    return {"icon": icon, "color": color}
