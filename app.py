from flask import Flask, render_template, request, flash, redirect, url_for, session
from DBMethods import UserRepository
import bcrypt
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import re
from pathlib import Path
from werkzeug.utils import secure_filename
from acc_recovery import send_recovery_email, send_username_email, generate_hashed_password

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
SECRET_KEY = os.getenv("SECRET_KEY")
app.secret_key = SECRET_KEY

repo = UserRepository("hornethelpers.db")
UPLOAD_FOLDER = Path("static/uploads/profile_photos")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ADMIN_REGISTRATION_PIN = os.getenv("ADMIN_REGISTRATION_PIN")
ORGANIZER_REGISTRATION_PIN = os.getenv("ORGANIZER_REGISTRATION_PIN")

ALLOWED_ACCOUNT_TYPES = {"Volunteer", "Organizer", "Admin"}


def get_current_username():
    return session.get("username")


def is_valid_email(email):
    valid_email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|net|org|edu|gov|me)$"
    return bool(re.match(valid_email_pattern, email))


def is_valid_password(password):
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(pattern, password))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/homepage")
def homepage():
    return render_template("homepage.html")

# Updated Routes for each user type. Checks if user is logged in and then redirects to appropriate homepage. If not logged in, redirects to login page.
@app.route("/volunteer/home")
def volunteer_home():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))
    user = repo.find_user(username)
    return render_template("volunteer_home.html", user=user)


@app.route("/organizer/home")
def organizer_home():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))
    user = repo.find_user(username)
    return render_template("organizer_home.html", user=user)


@app.route("/admin/home")
def admin_home():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))
    user = repo.find_user(username)
    return render_template("admin_home.html", user=user)


@app.route("/acc_login", methods=["GET", "POST"])
def acc_login():
    if request.method == "POST":
        username = request.form["user"].strip()
        password = request.form["password"].strip()

        user = repo.find_user(username)

        if not user:
            flash("Invalid username or password.")
            return redirect(url_for("acc_login"))

        if user.lockout_until:
            lockout_time = datetime.fromisoformat(user.lockout_until)
            if datetime.now() < lockout_time:
                flash("Account is locked. Please try again later.")
                return redirect(url_for("acc_login"))

        if bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            repo.clear_failed_attempts(user.id)

            session["user_id"] = user.id
            session["username"] = user.username

            if user.account_type == "Admin":
                return redirect(url_for("admin_home"))
            elif user.account_type == "Organizer":
                return redirect(url_for("organizer_home"))
            else:
                return redirect(url_for("volunteer_home"))
        else:
            failed_attempts = user.failed_attempts + 1

            if failed_attempts >= 5:
                lockout_time = datetime.now() + timedelta(minutes=15)
                repo.update_failed_attempts(user.id, failed_attempts, lockout_time.isoformat())
                flash("Too many failed attempts. Account is locked for 15 minutes.")
            else:
                repo.update_failed_attempts(user.id, failed_attempts)
                flash("Incorrect username or password. Please try again.")

            return redirect(url_for("acc_login"))

    return render_template("acc_login.html")

@app.route("/new_account", methods=["GET", "POST"])
def new_account():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        username = request.form["user"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        confirm_password = request.form["confirm_password"].strip()
        account_type = request.form.get("account_type", "Volunteer").strip()
        organization_name = ""
        career_center_role = ""

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("new_account"))

        if not is_valid_email(email):
            flash("Invalid email address.")
            return redirect(url_for("new_account"))

        if not is_valid_password(password):
            flash("Password must be 8+ characters with a letter and a number.")
            return redirect(url_for("new_account"))

        if account_type not in ALLOWED_ACCOUNT_TYPES:
            flash("Please select a valid account type.")
            return redirect(url_for("new_account"))

        if repo.find_user(username) or repo.find_by_email(email):
            flash("Username or Email already exists.")
            return redirect(url_for("new_account"))

# Checks appropriate fields based on account type selected. Organizer requires organization name and registration pin. Admin requires career center role and registration pin.
        if account_type == "Organizer":
            organization_name = request.form.get("organization_name", "").strip()
            organizer_pin = request.form.get("organizer_pin", "").strip()
            if not organization_name:
                flash("Organization name is required for organizer registration.")
                return redirect(url_for("new_account"))
            if organizer_pin != ORGANIZER_REGISTRATION_PIN:
                flash("Invalid organizer registration pin.")
                return redirect(url_for("new_account"))

        if account_type == "Admin":
            career_center_role = request.form.get("career_center_role", "").strip()
            admin_pin = request.form.get("admin_pin", "").strip()
            if not career_center_role:
                flash("Career center role is required for admin registration.")
                return redirect(url_for("new_account"))
            if admin_pin != ADMIN_REGISTRATION_PIN:
                flash("Invalid admin registration pin.")
                return redirect(url_for("new_account"))

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        result_message = repo.add_user(
            username,
            hashed_password,
            full_name,
            email,
            account_type,
            organization_name=organization_name,
            career_center_role=career_center_role
        )

        if result_message == "User Added.":
            created_user = repo.find_user(username)
            if created_user:
                session["user_id"] = created_user.id
                session["username"] = created_user.username

            flash("Account created successfully!")
            if account_type == "Admin":
                return redirect(url_for("admin_home"))
            if account_type == "Organizer":
                return redirect(url_for("organizer_home"))
            return redirect(url_for("volunteer_home"))

        flash(f"Error: {result_message}")
        return redirect(url_for("new_account"))

    return render_template("new_account.html")



@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("acc_login"))


@app.route("/forgot_username", methods=["GET", "POST"])
def forgot_username():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if not is_valid_email(email):
            flash("invalid email entered.")
            return redirect(url_for("forgot_username"))

        user = repo.find_by_email(email)

        if user:
            send_username_email(email, user.username)

        flash("If this email is associated with an account, you should receive an email shortly!")
    return render_template("forgot_username.html")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if not is_valid_email(email):
            flash("invalid email entered.")
            return redirect(url_for("forgot_password"))

        user = repo.find_by_email(email)

        if user:
            reset_token = secrets.token_urlsafe(32)
            reset_token_expiry = datetime.now() + timedelta(hours=1)

            repo.set_reset_token(user.id, reset_token, reset_token_expiry.isoformat())

            send_recovery_email(email, reset_token)

        flash("If an account exists, you should receive a password reset link!")
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = repo.find_user_by_reset_token(token)

    if (
        not user
        or not user["reset_token_expiry"]
        or datetime.fromisoformat(user["reset_token_expiry"]) < datetime.now()
    ):
        flash("Invalid or expired reset link.")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("reset_password", token=token))

        if not is_valid_password(new_password):
            flash("Password must be at least 8 characters long and must contain at least 1 letter and number.")
            return redirect(url_for("reset_password", token=token))

        hashed_password = generate_hashed_password(new_password)

        repo.change_password(user["username"], hashed_password)
        repo.clear_reset_token(user["id"])

        flash("Password reset successfully.")
        return redirect(url_for("acc_login"))

    return render_template("reset_password.html", token=token)


@app.route("/account")
def account():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))

    user = repo.find_user(username)
    return render_template("account.html", user=user)


@app.route("/account/edit")
def account_edit():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))

    user = repo.find_user(username)
    return render_template("account_edit.html", user=user)

@app.route("/account/password")
def account_password():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))

    user = repo.find_user(username)
    return render_template("account_password.html", user=user)

@app.route("/account/password/update", methods=["POST"])
def update_account_password():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))

    user = repo.find_user(username)
    if not user:
        return redirect(url_for("acc_login"))

    current_password = request.form["current_password"].strip()
    new_password = request.form["new_password"].strip()
    confirm_password = request.form["confirm_password"].strip()

    if not bcrypt.checkpw(current_password.encode("utf-8"), user.password.encode("utf-8")):
        return render_template(
            "account_password.html",
            user=user,
            message="Current password is incorrect.",
            success=False
        )

    if new_password != confirm_password:
        return render_template(
            "account_password.html",
            user=user,
            message="New passwords do not match.",
            success=False
        )

    if not is_valid_password(new_password):
        return render_template(
            "account_password.html",
            user=user,
            message="Password must be at least 8 characters long and contain at least 1 letter and 1 number.",
            success=False
        )

    hashed_password = generate_hashed_password(new_password)
    repo.change_password(username, hashed_password)

    return render_template(
        "account_password.html",
        user=user,
        message="Password updated successfully.",
        success=True
    )

@app.route("/account/update", methods=["POST"])
def update_account():
    current_username = get_current_username()
    if not current_username:
        return redirect(url_for("acc_login"))

    current_user = repo.find_user(current_username)
    if not current_user:
        return redirect(url_for("acc_login"))

    new_username = request.form["username"].strip()
    full_name = request.form["full_name"].strip()
    email = request.form["email"].strip()
    bio = request.form["bio"].strip()

    photo = request.files.get("profile_photo")
    profile_photo_path = None

    if photo and photo.filename:
        if not allowed_file(photo.filename):
            user = repo.find_user(current_username)
            return render_template(
                "account_edit.html",
                user=user,
                message="Invalid file type. Please upload a PNG, JPG, or JPEG image.",
                success=False
            )

        extension = photo.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(f"user_{current_user.id}.{extension}")
        save_path = UPLOAD_FOLDER / filename
        photo.save(save_path)
        profile_photo_path = f"uploads/profile_photos/{filename}"

    success, message = repo.update_user(
        current_username,
        new_username,
        full_name,
        email,
        bio,
        profile_photo_path
    )

    if success:
        session["username"] = new_username
        return redirect(url_for("account"))

    user = repo.find_user(current_username)
    return render_template(
        "account_edit.html",
        user=user,
        message=message,
        success=success
    )


if __name__ == "__main__":
    repo.initialize()
    if not SECRET_KEY or not ADMIN_REGISTRATION_PIN or not ORGANIZER_REGISTRATION_PIN:
        raise ValueError("SECRET_KEY, ADMIN_REGISTRATION_PIN and ORGANIZER_REGISTRATION_PIN must be set in environment variables")
    app.run(debug=True)

@app.route("/eventCalendar")
def event_calendar():
    from eventCalendar import get_calendar_data
    today = datetime.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)

    data = get_calendar_data(year, month)

    return render_template("eventCalendar.html", today=today, **data)