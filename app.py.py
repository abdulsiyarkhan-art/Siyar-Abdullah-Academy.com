"""
Siyar Abdullah Academy — Backend API
Flask + SQLAlchemy REST API skeleton.

This is a real, runnable backend structure matching the frontend's data
model. It is NOT connected to the demo frontend (index.html) automatically —
the frontend currently uses in-memory sample data for demonstration purposes.
To wire them together, point the frontend's fetch() calls at these endpoints
and adjust CORS settings as needed.

Run locally:
    pip install -r requirements.txt
    cp .env.example .env      # then edit values
    flask --app app run --debug

See README.md for full setup instructions.
"""

import os
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# ---------------------------------------------------------------------------
# App & config
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///academy.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB upload cap
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")

db = SQLAlchemy(app)

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov"}
ALLOWED_DOC_EXT = {"pdf", "docx", "pptx", "zip"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student")  # 'student' | 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship("Enrollment", backref="user", lazy=True)
    reviews = db.relationship("Review", backref="user", lazy=True)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))

    courses = db.relationship("Course", backref="category", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "image_url": self.image_url,
            "course_count": len(self.courses),
        }


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    instructor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    difficulty = db.Column(db.String(20), default="Beginner")
    price = db.Column(db.Float, default=0.0)
    duration_minutes = db.Column(db.Integer, default=0)
    thumbnail_url = db.Column(db.String(255))
    banner_url = db.Column(db.String(255))
    learning_objectives = db.Column(db.Text)  # newline-separated
    requirements = db.Column(db.Text)  # newline-separated
    tags = db.Column(db.String(300))  # comma-separated
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    modules = db.relationship("Module", backref="course", lazy=True, order_by="Module.order")
    enrollments = db.relationship("Enrollment", backref="course", lazy=True)
    reviews = db.relationship("Review", backref="course", lazy=True)

    def to_dict(self, include_curriculum=False):
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "description": self.description,
            "category": self.category.to_dict() if self.category else None,
            "instructor": self.instructor.to_dict() if self.instructor else None,
            "difficulty": self.difficulty,
            "price": self.price,
            "duration_minutes": self.duration_minutes,
            "thumbnail_url": self.thumbnail_url,
            "banner_url": self.banner_url,
            "learning_objectives": (self.learning_objectives or "").splitlines(),
            "requirements": (self.requirements or "").splitlines(),
            "tags": [t.strip() for t in (self.tags or "").split(",") if t.strip()],
            "is_published": self.is_published,
            "lesson_count": sum(len(m.lessons) for m in self.modules),
            "rating": self.average_rating(),
            "student_count": len(self.enrollments),
        }
        if include_curriculum:
            data["modules"] = [m.to_dict() for m in self.modules]
        return data

    def average_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)


class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)

    lessons = db.relationship("Lesson", backref="module", lazy=True, order_by="Lesson.order")

    def to_dict(self):
        return {"id": self.id, "title": self.title, "order": self.order,
                "lessons": [l.to_dict() for l in self.lessons]}


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    video_url = db.Column(db.String(255))
    content = db.Column(db.Text)
    resource_url = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer, default=5)
    order = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "video_url": self.video_url, "content": self.content,
            "resource_url": self.resource_url,
            "duration_minutes": self.duration_minutes, "order": self.order,
        }


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

    progress_entries = db.relationship("Progress", backref="enrollment", lazy=True)

    def percent_complete(self, total_lessons):
        if not total_lessons:
            return 0
        done = sum(1 for p in self.progress_entries if p.completed)
        return round((done / total_lessons) * 100)


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey("enrollment.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lesson.id"), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    file_url = db.Column(db.String(255), nullable=False)
    resource_type = db.Column(db.String(50))  # PDF, E-book, Worksheet...
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        user = db.session.get(User, session["user_id"])
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return wrapper


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def allowed_file(filename, allowed_exts):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_exts


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.post("/api/auth/register")
def register():
    data = request.get_json(force=True) or {}
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not all([name, email, password]):
        return jsonify({"error": "name, email, and password are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists"}), 409
    user = User(name=name, email=email, role="student")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    return jsonify(user.to_dict()), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(force=True) or {}
    email, password = data.get("email"), data.get("password")
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401
    session["user_id"] = user.id
    return jsonify(user.to_dict())


@app.post("/api/auth/logout")
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out"})


@app.get("/api/auth/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user.to_dict())


# ---------------------------------------------------------------------------
# Course routes
# ---------------------------------------------------------------------------
@app.get("/api/courses")
def list_courses():
    q = Course.query.filter_by(is_published=True)
    category = request.args.get("category")
    difficulty = request.args.get("difficulty")
    search = request.args.get("q")
    if category:
        q = q.join(Category).filter(Category.slug == category)
    if difficulty:
        q = q.filter(Course.difficulty == difficulty)
    if search:
        q = q.filter(Course.title.ilike(f"%{search}%"))
    return jsonify([c.to_dict() for c in q.all()])


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    return jsonify(course.to_dict(include_curriculum=True))


@app.post("/api/courses")
@admin_required
def create_course():
    data = request.get_json(force=True) or {}
    course = Course(
        title=data["title"],
        slug=data["title"].lower().replace(" ", "-"),
        description=data.get("description"),
        category_id=data.get("category_id"),
        instructor_id=data.get("instructor_id"),
        difficulty=data.get("difficulty", "Beginner"),
        price=data.get("price", 0),
        duration_minutes=data.get("duration_minutes", 0),
        thumbnail_url=data.get("thumbnail_url"),
        learning_objectives="\n".join(data.get("learning_objectives", [])),
        requirements="\n".join(data.get("requirements", [])),
        tags=",".join(data.get("tags", [])),
        is_published=data.get("publish", False),
    )
    db.session.add(course)
    db.session.commit()

    for m_idx, module_data in enumerate(data.get("modules", [])):
        module = Module(course_id=course.id, title=module_data["title"], order=m_idx)
        db.session.add(module)
        db.session.flush()
        for l_idx, lesson_title in enumerate(module_data.get("lessons", [])):
            db.session.add(Lesson(module_id=module.id, title=lesson_title, order=l_idx))
    db.session.commit()
    return jsonify(course.to_dict(include_curriculum=True)), 201


@app.put("/api/courses/<int:course_id>")
@admin_required
def update_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    data = request.get_json(force=True) or {}
    for field in ["title", "description", "difficulty", "price", "thumbnail_url", "is_published"]:
        if field in data:
            setattr(course, field, data[field])
    db.session.commit()
    return jsonify(course.to_dict())


@app.delete("/api/courses/<int:course_id>")
@admin_required
def delete_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    db.session.delete(course)
    db.session.commit()
    return jsonify({"message": "Course deleted"})


# ---------------------------------------------------------------------------
# Category routes
# ---------------------------------------------------------------------------
@app.get("/api/categories")
def list_categories():
    return jsonify([c.to_dict() for c in Category.query.all()])


@app.post("/api/categories")
@admin_required
def create_category():
    data = request.get_json(force=True) or {}
    cat = Category(
        name=data["name"],
        slug=data["name"].lower().replace(" ", "-"),
        description=data.get("description"),
        image_url=data.get("image_url"),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


# ---------------------------------------------------------------------------
# Enrollment & progress routes
# ---------------------------------------------------------------------------
@app.post("/api/enrollments")
@login_required
def create_enrollment():
    data = request.get_json(force=True) or {}
    course_id = data.get("course_id")
    existing = Enrollment.query.filter_by(user_id=session["user_id"], course_id=course_id).first()
    if existing:
        return jsonify({"message": "Already enrolled"}), 200
    enrollment = Enrollment(user_id=session["user_id"], course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()
    return jsonify({"message": "Enrolled successfully", "enrollment_id": enrollment.id}), 201


@app.get("/api/user/courses")
@login_required
def user_courses():
    enrollments = Enrollment.query.filter_by(user_id=session["user_id"]).all()
    result = []
    for e in enrollments:
        total_lessons = sum(len(m.lessons) for m in e.course.modules)
        result.append({
            "course": e.course.to_dict(),
            "progress_percent": e.percent_complete(total_lessons),
            "enrolled_at": e.enrolled_at.isoformat(),
        })
    return jsonify(result)


@app.post("/api/user/progress")
@login_required
def update_progress():
    data = request.get_json(force=True) or {}
    lesson_id, enrollment_id = data.get("lesson_id"), data.get("enrollment_id")
    progress = Progress.query.filter_by(enrollment_id=enrollment_id, lesson_id=lesson_id).first()
    if not progress:
        progress = Progress(enrollment_id=enrollment_id, lesson_id=lesson_id)
        db.session.add(progress)
    progress.completed = True
    progress.completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Progress updated"})


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------
@app.post("/api/courses/<int:course_id>/reviews")
@login_required
def create_review(course_id):
    data = request.get_json(force=True) or {}
    review = Review(
        course_id=course_id,
        user_id=session["user_id"],
        rating=data.get("rating", 5),
        text=data.get("text", ""),
    )
    db.session.add(review)
    db.session.commit()
    return jsonify({"message": "Review submitted"}), 201


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
@app.post("/api/contact")
def contact():
    data = request.get_json(force=True) or {}
    required = ["name", "email", "message"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "name, email, and message are required"}), 400
    msg = ContactMessage(
        name=data["name"], email=data["email"],
        subject=data.get("subject", ""), message=data["message"],
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({"message": "Message received"}), 201


# ---------------------------------------------------------------------------
# File uploads (thumbnails, videos, resources)
# ---------------------------------------------------------------------------
@app.post("/api/uploads")
@admin_required
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    allowed = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT | ALLOWED_DOC_EXT
    if not allowed_file(file.filename, allowed):
        return jsonify({"error": "File type not allowed"}), 400
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    dest = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(dest)
    return jsonify({"message": "Uploaded", "path": dest}), 201


# ---------------------------------------------------------------------------
# Admin summary
# ---------------------------------------------------------------------------
@app.get("/api/admin/summary")
@admin_required
def admin_summary():
    return jsonify({
        "total_students": User.query.filter_by(role="student").count(),
        "total_courses": Course.query.count(),
        "total_lessons": Lesson.query.count(),
        "total_enrollments": Enrollment.query.count(),
        "total_categories": Category.query.count(),
    })


# ---------------------------------------------------------------------------
# CLI: seed sample data
# ---------------------------------------------------------------------------
@app.cli.command("seed")
def seed():
    """Populate the database with sample categories, an admin user, and one course."""
    db.create_all()
    if not User.query.filter_by(email="admin@siyarabdullah.academy").first():
        admin = User(name="Siyar Abdullah", email="admin@siyarabdullah.academy", role="admin")
        admin.set_password(os.environ.get("SEED_ADMIN_PASSWORD", "change-me"))
        db.session.add(admin)

    cat_names = ["Programming", "Web Development", "Artificial Intelligence",
                 "Data Science", "Cybersecurity", "Computer Fundamentals", "Microsoft Office"]
    for name in cat_names:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name, slug=name.lower().replace(" ", "-")))
    db.session.commit()
    print("Seed complete. Log in with admin@siyarabdullah.academy / your SEED_ADMIN_PASSWORD.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
