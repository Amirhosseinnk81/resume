"""
Admin forms.

This file existed but was empty, while Flask-WTF sat in requirements.txt
being used for nothing but CSRF. Validation was instead done by hand in
routes.py: ~60 lines per view of `request.form.get(...).strip()`, manual int
parsing, and an `errors` list rebuilt on every branch — which is most of why
routes.py reached 779 lines.

Declaring the fields once gives type coercion, length limits, URL and file
validation, and error re-rendering for free, and it means the admin
templates can render field errors instead of a flat list.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    FieldList,
    FormField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from repositories.settings_repository import SKILL_CATEGORIES

PROJECT_STATUSES = [
    ("completed", "تکمیل‌شده"),
    ("in-progress", "در حال انجام"),
    ("planned", "برنامه‌ریزی‌شده"),
]

LANGUAGES = [("fa", "فارسی"), ("en", "English")]

SKILL_CATEGORY_CHOICES = [
    ("languages", "زبان‌ها"),
    ("frameworks", "فریم‌ورک‌ها"),
    ("databases", "پایگاه داده"),
    ("tools", "ابزارها"),
]


class CommaSeparatedField(StringField):
    """
    A text input that round-trips a list.

    The admin templates present technologies/features as one comma-separated
    text box, which the old routes split by hand in two places each. Doing
    it in the field keeps both directions in one spot.
    """

    def _value(self):
        if isinstance(self.data, (list, tuple)):
            return "، ".join(self.data)
        return self.data or ""

    def process_formdata(self, valuelist):
        raw = valuelist[0] if valuelist else ""
        # Accept both the ASCII and the Persian comma.
        for separator in ("،", ";"):
            raw = raw.replace(separator, ",")
        self.data = [part.strip() for part in raw.split(",") if part.strip()]


class LoginForm(FlaskForm):
    username = StringField("نام کاربری", validators=[DataRequired(), Length(max=100)])
    password = PasswordField("رمز عبور", validators=[DataRequired(), Length(max=200)])
    remember = BooleanField("مرا به خاطر بسپار")


class ProjectForm(FlaskForm):

    title = StringField(
        "عنوان پروژه",
        validators=[DataRequired("عنوان پروژه الزامی است."), Length(max=200)],
    )
    description = TextAreaField(
        "توضیحات",
        validators=[DataRequired("توضیحات پروژه الزامی است."), Length(max=5000)],
    )

    # Optional English variants; empty falls back to the Persian text.
    title_en = StringField("عنوان (انگلیسی)", validators=[Optional(), Length(max=200)])
    description_en = TextAreaField(
        "توضیحات (انگلیسی)", validators=[Optional(), Length(max=5000)]
    )
    technologies = CommaSeparatedField(
        "تکنولوژی‌ها",
        validators=[DataRequired("حداقل یک تکنولوژی وارد کنید.")],
    )
    features = CommaSeparatedField("ویژگی‌ها", validators=[Optional()])

    github = StringField(
        "لینک گیت‌هاب",
        validators=[Optional(), URL(message="لینک گیت‌هاب معتبر نیست."), Length(max=500)],
    )
    demo = StringField(
        "لینک دمو",
        validators=[Optional(), URL(message="لینک دمو معتبر نیست."), Length(max=500)],
    )
    image = StringField("نام فایل تصویر", validators=[Optional(), Length(max=300)])

    status = SelectField(
        "وضعیت",
        choices=PROJECT_STATUSES,
        default="completed",
        validators=[DataRequired("وضعیت پروژه نامعتبر است.")],
    )
    year = IntegerField(
        "سال",
        validators=[
            Optional(),
            NumberRange(min=1990, max=2100, message="سال پروژه معتبر نیست."),
        ],
    )

    # Lets each project carry a concrete number the way the reference
    # portfolios do ("GitHub stars", "8,281") instead of prose only.
    metric_label = StringField("عنوان سنجه", validators=[Optional(), Length(max=100)])
    metric_value = StringField("مقدار سنجه", validators=[Optional(), Length(max=100)])

    def to_dict(self):
        return {
            "title": self.title.data.strip(),
            "title_en": (self.title_en.data or "").strip(),
            "description": self.description.data.strip(),
            "description_en": (self.description_en.data or "").strip(),
            "technologies": self.technologies.data,
            "features": self.features.data,
            "github": (self.github.data or "").strip(),
            "demo": (self.demo.data or "").strip(),
            "image": (self.image.data or "").strip(),
            "status": self.status.data,
            "year": self.year.data,
            "metric_label": (self.metric_label.data or "").strip(),
            "metric_value": (self.metric_value.data or "").strip(),
        }


class ArticleForm(FlaskForm):
    """
    `file` is optional here and made required for the create view via
    `require_file()`, so editing an article without re-uploading its PDF
    keeps working.
    """

    title = StringField(
        "عنوان مقاله",
        validators=[DataRequired("عنوان مقاله الزامی است."), Length(max=300)],
    )
    abstract = TextAreaField(
        "چکیده",
        validators=[DataRequired("چکیده مقاله الزامی است."), Length(max=5000)],
    )
    authors = StringField("نویسندگان", validators=[Optional(), Length(max=300)])

    # Optional English variants; empty falls back to the Persian text.
    title_en = StringField("عنوان (انگلیسی)", validators=[Optional(), Length(max=300)])
    abstract_en = TextAreaField(
        "چکیده (انگلیسی)", validators=[Optional(), Length(max=5000)]
    )
    authors_en = StringField(
        "نویسندگان (انگلیسی)", validators=[Optional(), Length(max=300)]
    )
    year = IntegerField(
        "سال انتشار",
        validators=[
            Optional(),
            NumberRange(min=1900, max=2100, message="سال انتشار معتبر نیست."),
        ],
    )
    language = SelectField("زبان", choices=LANGUAGES, default="fa")
    image = StringField("نام فایل تصویر", validators=[Optional(), Length(max=300)])

    file = FileField(
        "فایل PDF",
        validators=[
            Optional(),
            FileAllowed(["pdf"], "فقط فایل PDF مجاز است."),
        ],
    )

    def require_file(self):
        self.file.validators = [
            FileRequired("فایل PDF مقاله الزامی است."),
            FileAllowed(["pdf"], "فقط فایل PDF مجاز است."),
        ]
        return self

    def to_dict(self):
        return {
            "title": self.title.data.strip(),
            "title_en": (self.title_en.data or "").strip(),
            "abstract": self.abstract.data.strip(),
            "abstract_en": (self.abstract_en.data or "").strip(),
            "authors": (self.authors.data or "").strip(),
            "authors_en": (self.authors_en.data or "").strip(),
            "year": self.year.data,
            "language": self.language.data,
            "image": (self.image.data or "").strip(),
        }


class SkillEntryForm(FlaskForm):
    """Subform for one skill row. Meta.csrf off: the parent form carries it."""

    class Meta:
        csrf = False

    name = StringField("مهارت", validators=[Optional(), Length(max=100)])
    category = SelectField("دسته", choices=SKILL_CATEGORY_CHOICES, default="tools")


class SettingsForm(FlaskForm):

    github = StringField(
        "GitHub", validators=[Optional(), URL(message="لینک GitHub معتبر نیست."), Length(max=500)]
    )
    linkedin = StringField(
        "LinkedIn", validators=[Optional(), URL(message="لینک LinkedIn معتبر نیست."), Length(max=500)]
    )
    twitter = StringField(
        "X / Twitter", validators=[Optional(), URL(message="لینک X معتبر نیست."), Length(max=500)]
    )

    skills = FieldList(FormField(SkillEntryForm), min_entries=0)

    resume = FileField(
        "فایل رزومه (PDF)",
        validators=[Optional(), FileAllowed(["pdf"], "فایل رزومه باید PDF باشد.")],
    )

    def to_dict(self):
        skills = []
        for entry in self.skills.entries:
            name = (entry.form.name.data or "").strip()
            if not name:
                continue
            category = entry.form.category.data
            if category not in SKILL_CATEGORIES:
                category = "tools"
            skills.append({"name": name, "category": category})

        return {
            "socials": {
                "github": (self.github.data or "").strip(),
                "linkedin": (self.linkedin.data or "").strip(),
                "twitter": (self.twitter.data or "").strip(),
            },
            "skills": skills,
        }


class ContactForm(FlaskForm):
    """
    The public contact form. Previously validated with three inline
    `if not x` checks and no length or email-shape validation at all, so a
    multi-megabyte "message" or a malformed address went straight into
    storage and into the notification email.
    """

    name = StringField(
        "نام", validators=[DataRequired("لطفاً همهٔ فیلدها را پر کنید."), Length(max=200)]
    )
    email = StringField(
        "ایمیل",
        validators=[DataRequired("لطفاً همهٔ فیلدها را پر کنید."), Length(max=300)],
    )
    message = TextAreaField(
        "پیام",
        validators=[
            DataRequired("لطفاً همهٔ فیلدها را پر کنید."),
            Length(min=5, max=5000, message="پیام باید بین ۵ تا ۵۰۰۰ کاراکتر باشد."),
        ],
    )
    # Honeypot: a field hidden with CSS that real visitors never fill in.
    website = StringField("Website", validators=[Optional()])

    def validate_email(self, field):
        """
        Deliberately permissive shape check rather than a strict RFC parser:
        requires something@something.tld and rejects whitespace, which is
        enough to catch typos and obvious junk without the `email_validator`
        dependency.
        """
        value = (field.data or "").strip()
        if (
            " " in value
            or value.count("@") != 1
            or "." not in value.rsplit("@", 1)[-1]
            or value.startswith("@")
            or value.endswith("@")
            or value.endswith(".")
        ):
            raise ValidationError("آدرس ایمیل معتبر نیست.")
