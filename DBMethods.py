import sqlite3
import re
from datetime import datetime
from typing import List, Optional


# =========================================================
# USER MODEL
# =========================================================

class User:
    def __init__(
        self,
        id: int,
        username: str,
        password: str,
        full_name: str,
        email: str,
        bio: str,
        account_type: str = "Volunteer",
        organization_name: str = "",
        career_center_role: str = "",
        profile_photo: str = "",
        failed_attempts: int = 0,
        lockout_until: str = None,
        reset_token: str = None,
        reset_token_expiry: str = None
    ):
        self.id = id
        self.username = username
        self.password = password
        self.full_name = full_name
        self.email = email
        self.bio = bio
        self.account_type = account_type
        self.organization_name = organization_name
        self.career_center_role = career_center_role
        self.profile_photo = profile_photo
        self.failed_attempts = failed_attempts
        self.lockout_until = lockout_until
        self.reset_token = reset_token
        self.reset_token_expiry = reset_token_expiry


# =========================================================
# EVENT MODEL
# =========================================================

class Event:
    def __init__(
        self,
        id: int,
        title: str,
        description: str,
        location: str,
        start_datetime: str,
        end_datetime: str,
        created_by_username: str,
        created_by_account_type: str,
        organization_name: str
    ):
        self.id = id
        self.title = title
        self.description = description
        self.location = location
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.created_by_username = created_by_username
        self.created_by_account_type = created_by_account_type
        self.organization_name = organization_name


# =========================================================
# USER REPOSITORY
# =========================================================

class UserRepository:

    def __init__(self, database_path: str):
        self.database_path = database_path

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _validate_user(
        self,
        username,
        password,
        full_name,
        email,
        account_type
    ):

        patterns = {
            "username": r".+",
            "password": r".+",
            "full_name": r".+",
            "email": (
                r"^[a-zA-Z0-9._%+-]+@"
                r"[a-zA-Z0-9.-]+\."
                r"(com|gov|edu|net|org|me)$"
            )
        }

        allowed_types = {
            "Volunteer",
            "Organizer",
            "Admin"
        }

        if not re.match(patterns["username"], username):
            return False, "Invalid username"

        if not re.match(patterns["password"], password):
            return False, "Invalid password"

        if not re.match(patterns["full_name"], full_name):
            return False, "Invalid full name"

        if not re.match(patterns["email"], email):
            return False, "Invalid email"

        if account_type not in allowed_types:
            return False, "Invalid account type"

        return True, ""

    # =====================================================
    # INITIALIZE USERS TABLE
    # =====================================================

    def initialize(self):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    fullName TEXT NOT NULL DEFAULT '',
                    bio TEXT NOT NULL DEFAULT '',
                    account_type TEXT NOT NULL DEFAULT 'Volunteer',
                    organization_name TEXT NOT NULL DEFAULT '',
                    career_center_role TEXT NOT NULL DEFAULT '',
                    profile_photo TEXT NOT NULL DEFAULT '',
                    failed_attempts INTEGER DEFAULT 0,
                    lockout_until TEXT DEFAULT NULL,
                    reset_token TEXT DEFAULT NULL,
                    reset_token_expiry TEXT DEFAULT NULL
                )
            """)

            columns_to_add = [
                ("fullName", "TEXT NOT NULL DEFAULT ''"),
                ("bio", "TEXT NOT NULL DEFAULT ''"),
                ("account_type", "TEXT NOT NULL DEFAULT 'Volunteer'"),
                ("organization_name", "TEXT NOT NULL DEFAULT ''"),
                ("career_center_role", "TEXT NOT NULL DEFAULT ''"),
                ("profile_photo", "TEXT NOT NULL DEFAULT ''"),
                ("failed_attempts", "INTEGER DEFAULT 0"),
            ]

            for col_name, col_type in columns_to_add:

                try:
                    cursor.execute(
                        f"""
                        ALTER TABLE users
                        ADD COLUMN {col_name} {col_type}
                        """
                    )

                except sqlite3.OperationalError as e:

                    if "duplicate column name" not in str(e).lower():
                        raise

            conn.commit()

    # =====================================================
    # ADD USER
    # =====================================================

    def add_user(
        self,
        username,
        password,
        full_name,
        email,
        account_type="Volunteer",
        organization_name="",
        career_center_role="",
        bio="",
        profile_photo=""
    ):

        valid, message = self._validate_user(
            username,
            password,
            full_name,
            email,
            account_type
        )

        if not valid:
            return message

        try:

            with self._connect() as conn:

                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO users (
                        username,
                        email,
                        password,
                        fullName,
                        bio,
                        account_type,
                        organization_name,
                        career_center_role,
                        profile_photo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    username,
                    email,
                    password,
                    full_name,
                    bio,
                    account_type,
                    organization_name,
                    career_center_role,
                    profile_photo
                ))

                conn.commit()

            return "User Added."

        except Exception as e:
            return f"Error: {e}"

    # =====================================================
    # LIST USERS
    # =====================================================

    def list_users(self) -> List[User]:

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    username,
                    password,
                    fullName,
                    email,
                    bio,
                    account_type,
                    organization_name,
                    career_center_role,
                    profile_photo
                FROM users
            """)

            rows = cursor.fetchall()

            return [User(*row) for row in rows]

    # =====================================================
    # FIND USER BY USERNAME
    # =====================================================

    def find_user(self, username) -> Optional[User]:

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    username,
                    password,
                    fullName,
                    email,
                    bio,
                    account_type,
                    organization_name,
                    career_center_role,
                    profile_photo,
                    failed_attempts,
                    lockout_until,
                    reset_token,
                    reset_token_expiry
                FROM users
                WHERE username = ?
            """, (username,))

            row = cursor.fetchone()

            if row:

                return User(
                    id=row[0],
                    username=row[1],
                    password=row[2],
                    full_name=row[3],
                    email=row[4],
                    bio=row[5],
                    account_type=row[6],
                    organization_name=row[7] or "",
                    career_center_role=row[8] or "",
                    profile_photo=row[9] or "",
                    failed_attempts=row[10] or 0,
                    lockout_until=row[11],
                    reset_token=row[12],
                    reset_token_expiry=row[13]
                )

            return None

    # =====================================================
    # FIND USER BY EMAIL
    # =====================================================

    def find_by_email(self, email: str) -> Optional[User]:

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    username,
                    password,
                    fullName,
                    email,
                    bio,
                    account_type,
                    organization_name,
                    career_center_role,
                    profile_photo,
                    failed_attempts,
                    lockout_until,
                    reset_token,
                    reset_token_expiry
                FROM users
                WHERE email = ?
            """, (email,))

            row = cursor.fetchone()

            if row:

                return User(
                    id=row[0],
                    username=row[1],
                    password=row[2],
                    full_name=row[3],
                    email=row[4],
                    bio=row[5],
                    account_type=row[6],
                    organization_name=row[7] or "",
                    career_center_role=row[8] or "",
                    profile_photo=row[9] or "",
                    failed_attempts=row[10] or 0,
                    lockout_until=row[11],
                    reset_token=row[12],
                    reset_token_expiry=row[13]
                )

            return None

    # =====================================================
    # PASSWORD MANAGEMENT
    # =====================================================

    def change_password(self, username, new_password):

        if not re.match(r".+", new_password):
            return False

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET password = ?
                WHERE username = ?
            """, (new_password, username))

            conn.commit()

        return True

    # =====================================================
    # UPDATE USER
    # =====================================================

    def update_user(
        self,
        current_username,
        new_username,
        new_full_name,
        new_email,
        new_bio,
        new_profile_photo=None
    ):

        if not re.match(r".+", new_username):
            return False, "Invalid username"

        if not re.match(r".+", new_full_name):
            return False, "Invalid full name"

        if not re.match(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|gov|edu|net|org|me)$",
            new_email
        ):
            return False, "Invalid email"

        try:

            with self._connect() as conn:

                cursor = conn.cursor()

                if new_profile_photo is not None:

                    cursor.execute("""
                        UPDATE users
                        SET
                            username = ?,
                            fullName = ?,
                            email = ?,
                            bio = ?,
                            profile_photo = ?
                        WHERE username = ?
                    """, (
                        new_username,
                        new_full_name,
                        new_email,
                        new_bio,
                        new_profile_photo,
                        current_username
                    ))

                else:

                    cursor.execute("""
                        UPDATE users
                        SET
                            username = ?,
                            fullName = ?,
                            email = ?,
                            bio = ?
                        WHERE username = ?
                    """, (
                        new_username,
                        new_full_name,
                        new_email,
                        new_bio,
                        current_username
                    ))

                conn.commit()

            return True, "Account updated successfully."

        except Exception as e:
            return False, f"Error: {e}"

    # =====================================================
    # RESET TOKEN METHODS
    # =====================================================

    def find_user_by_reset_token(self, token: str):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    username,
                    password,
                    fullName,
                    email,
                    bio,
                    account_type,
                    organization_name,
                    career_center_role,
                    profile_photo,
                    failed_attempts,
                    lockout_until,
                    reset_token,
                    reset_token_expiry
                FROM users
                WHERE reset_token = ?
            """, (token,))

            row = cursor.fetchone()

            if row:

                return {
                    "id": row[0],
                    "username": row[1],
                    "password": row[2],
                    "fullName": row[3],
                    "email": row[4],
                    "bio": row[5],
                    "account_type": row[6],
                    "organization_name": row[7],
                    "career_center_role": row[8],
                    "profile_photo": row[9],
                    "failed_attempts": row[10],
                    "lockout_until": row[11],
                    "reset_token": row[12],
                    "reset_token_expiry": row[13]
                }

            return None

    def update_failed_attempts(
        self,
        user_id: int,
        failed_attempts: int,
        lockout_until: str = None
    ):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET failed_attempts = ?, lockout_until = ?
                WHERE id = ?
            """, (
                failed_attempts,
                lockout_until,
                user_id
            ))

            conn.commit()

    def clear_failed_attempts(self, user_id: int):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET failed_attempts = 0,
                    lockout_until = NULL
                WHERE id = ?
            """, (user_id,))

            conn.commit()

    def set_reset_token(
        self,
        user_id: int,
        token: str,
        expiry: str
    ):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET
                    reset_token = ?,
                    reset_token_expiry = ?
                WHERE id = ?
            """, (
                token,
                expiry,
                user_id
            ))

            conn.commit()

    def clear_reset_token(self, user_id: int):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET
                    reset_token = NULL,
                    reset_token_expiry = NULL,
                    failed_attempts = 0,
                    lockout_until = NULL
                WHERE id = ?
            """, (user_id,))

            conn.commit()

    # =====================================================
    # DELETE USER
    # =====================================================

    def delete_user(self, username):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM users
                WHERE username = ?
            """, (username,))

            conn.commit()

        return True


# =========================================================
# EVENT REPOSITORY
# =========================================================

class EventRepository:

    def __init__(self, database_path: str):
        self.database_path = database_path

    def _connect(self):
        return sqlite3.connect(self.database_path)

    # =====================================================
    # INITIALIZE EVENTS TABLE
    # =====================================================

    def initialize(self):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    location TEXT NOT NULL,
                    start_datetime TEXT NOT NULL,
                    end_datetime TEXT NOT NULL,
                    created_by_username TEXT NOT NULL,
                    created_by_account_type TEXT NOT NULL,
                    organization_name TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    # =====================================================
    # ADD EVENT
    # =====================================================

    def add_event(
        self,
        title,
        description,
        location,
        start_datetime,
        end_datetime,
        created_by_username,
        created_by_account_type,
        organization_name=""
    ):

        if not re.match(r"^.+$", title):
            return False, "Title is required."

        if not re.match(r"^.+$", description):
            return False, "Description is required."

        if not re.match(r"^.+$", location):
            return False, "Location is required."

        if not re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$",
            start_datetime
        ):
            return False, "Invalid start date/time format."

        if not re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$",
            end_datetime
        ):
            return False, "Invalid end date/time format."

        try:

            with self._connect() as conn:

                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id
                    FROM events
                    WHERE
                        title = ?
                        AND location = ?
                        AND start_datetime = ?
                """, (
                    title,
                    location,
                    start_datetime
                ))

                if cursor.fetchone():

                    return (
                        False,
                        "An event with the same title, "
                        "location, and start date/time "
                        "already exists."
                    )

                cursor.execute("""
                    INSERT INTO events (
                        title,
                        description,
                        location,
                        start_datetime,
                        end_datetime,
                        created_by_username,
                        created_by_account_type,
                        organization_name
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    title,
                    description,
                    location,
                    start_datetime,
                    end_datetime,
                    created_by_username,
                    created_by_account_type,
                    organization_name
                ))

                conn.commit()

            return True, "Event created successfully."

        except Exception as e:
            return False, f"Error: {e}"

    # =====================================================
    # LIST UPCOMING EVENTS
    # =====================================================

    def list_upcoming_events(self):

        now = datetime.now().isoformat(timespec='minutes')

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    title,
                    description,
                    location,
                    start_datetime,
                    end_datetime,
                    created_by_username,
                    created_by_account_type,
                    organization_name
                FROM events
                WHERE start_datetime >= ?
                ORDER BY start_datetime ASC
            """, (now,))

            rows = cursor.fetchall()

            return [Event(*row) for row in rows]

    # =====================================================
    # LIST EVENTS BY CREATOR
    # =====================================================

    def list_events_by_creator(self, username):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    title,
                    description,
                    location,
                    start_datetime,
                    end_datetime,
                    created_by_username,
                    created_by_account_type,
                    organization_name
                FROM events
                WHERE created_by_username = ?
                ORDER BY start_datetime ASC
            """, (username,))

            rows = cursor.fetchall()

            return [Event(*row) for row in rows]

    # =====================================================
    # LIST EVENTS BY ORGANIZATION
    # =====================================================

    def list_events_by_organization(self, organization_name):

        with self._connect() as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    title,
                    description,
                    location,
                    start_datetime,
                    end_datetime,
                    created_by_username,
                    created_by_account_type,
                    organization_name
                FROM events
                WHERE organization_name = ?
                ORDER BY start_datetime ASC
            """, (organization_name,))

            rows = cursor.fetchall()

            return [Event(*row) for row in rows]
