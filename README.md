# رزومه و نمونه‌کار — امیرحسین نعیمائی

[![CI](https://github.com/Amirhosseinnk81/resume/actions/workflows/ci.yml/badge.svg)](https://github.com/Amirhosseinnk81/resume/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)

وب‌اپ شخصی دوزبانه (فارسی/انگلیسی) برای ارائهٔ رزومه، پروژه‌ها و مقالات،
همراه با پنل مدیریت اختصاصی. با Flask و SQLAlchemy نوشته شده است.

> **چرا Flask و نه یک سایت استاتیک؟** این سایت نمونه‌کارِ یک توسعه‌دهندهٔ
> بک‌اند است؛ پنل مدیریت، لایهٔ دادهٔ آن، احراز هویت و APIها بخشی از همان
> چیزی هستند که باید نشان داده شوند. یک سایت استاتیک آن‌ها را حذف می‌کرد.

---

## فهرست

- [امکانات](#امکانات)
- [معماری](#معماری)
- [راه‌اندازی](#راهاندازی)
- [متغیرهای محیطی](#متغیرهای-محیطی)
- [پنل مدیریت](#پنل-مدیریت)
- [تست](#تست)
- [استقرار](#استقرار)
- [مهاجرت از نسخهٔ JSON](#مهاجرت-از-نسخهٔ-json)
- [نکات امنیتی](#نکات-امنیتی)

---

## امکانات

**بخش عمومی**

- صفحهٔ اصلی، پروژه‌ها، درباره‌من، مقالات و تماس
- دوزبانه (fa/rtl و en/ltr) با سوییچ زبان مبتنی بر session
- دارک‌مود با احترام به `prefers-color-scheme` سیستم‌عامل و ذخیرهٔ انتخاب کاربر
- صفحهٔ جزئیات برای هر پروژه و هر مقاله
- دانلود PDF مقالات و رزومه
- شمارش بازدید مقالات
- `sitemap.xml` و `robots.txt` تولیدشدهٔ داینامیک
- فید RSS در `/feed.xml`
- دادهٔ ساختاریافتهٔ JSON-LD (`Person`، `ScholarlyArticle`، `SoftwareSourceCode`، `BreadcrumbList`)
- مانیفست PWA برای نصب روی موبایل
- صفحات خطای سفارشی ۴۰۴ / ۴۲۹ / ۵۰۰
- فرم تماس با CSRF، honeypot، محدودسازی نرخ و ذخیره‌سازی پایدار

**پنل مدیریت (`/admin`)**

- احراز هویت با هش پسورد و محدودسازی نرخ تلاش ورود
- CRUD پروژه‌ها، مقالات (با آپلود PDF) و تنظیمات
- صندوق پیام‌های فرم تماس با وضعیت خوانده/نخوانده
- داشبورد آمار: بازدید روزانه، پربازدیدترین صفحات، مجموع بازدید مقالات

---

## معماری

```
app.py                      create_app() factory + روت‌های عمومی
config.py                   کلاس‌های کانفیگ (development / production / testing)
content.py                  محتوای ثابت: پروفایل، ترجمه‌ها، تجربه، تحصیلات
extensions.py               نمونه‌های افزونه‌ها (db, csrf, mail, limiter)
models.py                   مدل‌های SQLAlchemy
seo.py                      JSON-LD، تولید sitemap و RSS
wsgi.py                     نقطهٔ ورود production
gunicorn.conf.py            پیکربندی gunicorn

admin/
  __init__.py               Blueprint
  routes.py                 فقط لایهٔ HTTP
  auth.py                   بررسی اعتبارنامه و مدیریت session
  forms.py                  فرم‌های Flask-WTF و اعتبارسنجی
  utils.py                  سنیتایز و ذخیرهٔ فایل آپلودی
  decorators.py             @login_required
  dashboard_service.py      آمار داشبورد

repositories/               لایهٔ دسترسی به داده — روت‌ها هرگز مستقیم با مدل کار نمی‌کنند
  project_repository.py
  article_repository.py
  message_repository.py
  settings_repository.py
  pageview_repository.py

templates/                  قالب‌های Jinja2 (عمومی + admin/ + errors/)
static/                     CSS، JS و تصاویر
tests/                      ۱۲۰ تست pytest
scripts/
  generate_password_hash.py  ساخت هش پسورد ادمین
  migrate_json_to_db.py      مهاجرت یک‌بارهٔ data/*.json به دیتابیس
```

**اصول**

- **App factory** — `create_app(config_name)` اجازه می‌دهد اپ با کانفیگ تست
  ساخته شود. این پیش‌نیاز کل مجموعهٔ تست است.
- **لایهٔ repository** — روت‌ها و قالب‌ها فقط `dict` می‌بینند. به همین دلیل
  مهاجرت از JSON به SQLAlchemy هیچ روت یا قالبی را تغییر نداد.
- **اعتبارسنجی در فرم‌ها، نه در روت‌ها** — هر فیلد یک بار در `admin/forms.py`
  تعریف می‌شود.

---

## راه‌اندازی

نیازمندی: **Python 3.10+** (نسخهٔ production روی لیارا ۳.۱۰ است)

```bash
git clone https://github.com/Amirhosseinnk81/resume.git
cd resume
```

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

کپی کردن فایل نمونهٔ محیط:

```bash
cp .env.example .env
```

ساخت `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

ساخت هش پسورد ادمین:

```bash
python scripts/generate_password_hash.py
```

اجرا:

```bash
python app.py
```

سایت روی `http://127.0.0.1:5000` بالا می‌آید. دیتابیس SQLite در اولین اجرا
به‌طور خودکار در `data/resume.db` ساخته می‌شود.

---

## متغیرهای محیطی

همه در `.env.example` با توضیح آمده‌اند. ضروری‌ها:

| متغیر | توضیح |
|---|---|
| `SECRET_KEY` | کلید امضای session. **الزامی در production.** |
| `APP_ENV` | `development` \| `production` \| `testing` |
| `SITE_URL` | دامنهٔ عمومی؛ مبنای canonical، sitemap، RSS و JSON-LD |
| `DATABASE_URL` | خالی بماند → SQLite. برای Postgres: `postgresql+psycopg://...` |
| `ADMIN_USERNAME` | نام کاربری ادمین |
| `ADMIN_PASSWORD_HASH` | خروجی `scripts/generate_password_hash.py` |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | برای Gmail یک **App Password** لازم است، نه پسورد حساب |
| `CONTACT_RECIPIENT_EMAIL` | گیرندهٔ اعلان فرم تماس |
| `RATELIMIT_STORAGE_URI` | با بیش از یک worker روی Redis بگذارید |
| `FLASK_DEBUG` | فقط `1` برای دیباگ محلی. **هرگز در production.** |

---

## پنل مدیریت

`http://127.0.0.1:5000/admin`

پیش از اولین ورود، `ADMIN_USERNAME` و `ADMIN_PASSWORD_HASH` باید در `.env`
تنظیم شده باشند؛ در غیر این صورت ورود همیشه رد می‌شود (فرم خالی عبور نمی‌کند).

مهارت‌ها در پنل تنظیمات با **دسته‌بندی** ذخیره می‌شوند (زبان‌ها، فریم‌ورک‌ها،
پایگاه داده، ابزارها) و در صفحهٔ «درباره‌من» به‌شکل تگ نمایش داده می‌شوند.

---

## تست

```bash
pip install -r requirements-dev.txt
```

```bash
pytest
```

با گزارش پوشش:

```bash
pytest --cov=. --cov-report=term-missing
```

| فایل | موضوع |
|---|---|
| `test_public_pages.py` | رندر صفحات، ۴۰۴، سوییچ زبان، open redirect |
| `test_admin_crud.py` | CRUD پروژه/مقاله/تنظیمات، آپلود PDF |
| `test_security.py` | کنترل دسترسی، CSRF، هدرهای امنیتی، path traversal |
| `test_repositories.py` | قرارداد لایهٔ داده، مهاجرت مهارت‌های قدیمی |
| `test_uploads.py` | سنیتایز نام فایل (نام‌های فارسی، حملات traversal) |
| `test_contact.py` | اعتبارسنجی، honeypot، شکست SMTP |
| `test_pageviews.py` | شمارش بازدید و موارد استثنا |
| `test_seo.py` | sitemap، RSS، JSON-LD، canonical، hreflang |

CI روی هر push و PR اجرا می‌شود: تست روی Python 3.10/3.11/3.12/3.13، `ruff`،
`pip-audit`، و یک گام که اگر `.env` کامیت شده باشد build را می‌شکند.

---

## استقرار

### Docker Compose (پیشنهادی)

```bash
docker compose up -d --build
```

شامل Redis برای ذخیره‌سازی اشتراکی rate limit است. پوشه‌های `data/` و
`uploads/` به‌عنوان volume سوار می‌شوند تا دیتابیس و فایل‌ها با rebuild از
دست نروند.

### gunicorn به‌تنهایی

```bash
gunicorn -c gunicorn.conf.py wsgi:app
```

### Windows

```bash
waitress-serve --port=8000 wsgi:app
```

### نکات مهم production

- `python app.py` سرور توسعهٔ Flask را بالا می‌آورد — تک‌نخی و نامناسب برای
  اینترنت. از `wsgi:app` استفاده کنید.
- با `workers > 1` و rate limit در حافظه، هر worker سهمیهٔ خودش را اعمال
  می‌کند. `RATELIMIT_STORAGE_URI` را روی Redis بگذارید.
- SQLite برای این سایت با ترافیک خواندنی کافی است. اگر نوشتن زیاد شد،
  `DATABASE_URL` را به PostgreSQL تغییر دهید — کد تغییری لازم ندارد.
- `/healthz` برای probe سلامت در دسترس است.
- پشت یک reverse proxy، `FORWARDED_ALLOW_IPS` را تنظیم کنید تا rate limiter
  IP واقعی کاربر را ببیند.

---

## مهاجرت از نسخهٔ JSON

نسخه‌های قبلی داده را در `data/*.json` نگه می‌داشتند. برای انتقال یک‌بارهٔ
داده به دیتابیس:

```bash
python scripts/migrate_json_to_db.py
```

اسکریپت idempotent است (اجرای دوباره رکورد تکراری نمی‌سازد)، تعداد بازدید
مقالات را حفظ می‌کند، و مهارت‌های قدیمی با فرمت `{"name", "level"}` را به
فرمت دسته‌بندی‌شده تبدیل می‌کند. فایل‌های JSON دست‌نخورده به‌عنوان پشتیبان
باقی می‌مانند.

---

## نکات امنیتی

پیاده‌شده:

- CSRF روی همهٔ درخواست‌های تغییردهنده (Flask-WTF)
- هش پسورد با `werkzeug.security` و مقایسهٔ `hmac.compare_digest` برای نام کاربری
- محدودسازی نرخ: ۵ تلاش ورود در دقیقه، ۵ ارسال فرم تماس در ساعت
- کوکی session با `HttpOnly`، `SameSite=Lax` و `Secure` در production
- سنیتایز نام فایل آپلودی با حفظ حروف فارسی و بررسی containment مسیر
- محدودیت حجم آپلود (۲۰ مگابایت)
- فقط فایل‌هایی دانلود می‌شوند که واقعاً به یک مقاله متصل‌اند
- هدرهای `X-Content-Type-Options`، `X-Frame-Options`، `Referrer-Policy`، `Permissions-Policy`
- ریدایرکت‌ها فقط same-origin را دنبال می‌کنند
- `/admin` در `robots.txt` مستثنا شده و صفحهٔ ورود `noindex` است
- شمارش بازدید بدون IP، user agent یا کوکی

**هرگز `.env` را کامیت نکنید.** یک گام CI وجود دارد که اگر این اتفاق بیفتد
build را می‌شکند.

---

## مجوز

تمام حقوق محفوظ است. کد برای مطالعه در دسترس است؛ محتوا، متن رزومه و
تصاویر شخصی قابل استفادهٔ مجدد نیستند.
