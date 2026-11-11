from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")


# =====================================
# MYSQL DATABASE CONNECTION
# =====================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )



# =====================================
# HOME PAGE
# =====================================

@app.route("/")
def home():
    return render_template("index.html")


# =====================================
# REGISTRATION
# =====================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")

        # NGO details
        capacity_people = None
        food_requirements = None
        latitude = None
        longitude = None

        # Basic validation
        if not all([name, email, phone, address, role, password]):
            return render_template(
                "register.html",
                message="Please fill all required fields."
            )

        if role not in ["donor", "ngo"]:
            return render_template(
                "register.html",
                message="Please select a valid account type."
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                message="Password must contain at least 8 characters."
            )

        # NGO details validation
        if role == "ngo":

            try:
                capacity_people = int(
                    request.form.get("capacity_people", "")
                )

                food_requirements = request.form.get(
                    "food_requirements", ""
                ).strip()

                latitude = float(
                    request.form.get("latitude", "")
                )

                longitude = float(
                    request.form.get("longitude", "")
                )

                if capacity_people <= 0:
                    raise ValueError()

                if not food_requirements:
                    raise ValueError()

                if not (-90 <= latitude <= 90):
                    raise ValueError()

                if not (-180 <= longitude <= 180):
                    raise ValueError()

            except (ValueError, TypeError):
                return render_template(
                    "register.html",
                    message="Please enter valid NGO details."
                )

        hashed_password = generate_password_hash(password)

        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO users (
                    name,
                    email,
                    phone,
                    address,
                    role,
                    password,
                    capacity_people,
                    food_requirements,
                    latitude,
                    longitude
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                name,
                email,
                phone,
                address,
                role,
                hashed_password,
                capacity_people,
                food_requirements,
                latitude,
                longitude
            ))

            db.commit()

            return render_template(
                "register.html",
                message="Registration successful! Please login."
            )

        except mysql.connector.IntegrityError:
            return render_template(
                "register.html",
                message="This email is already registered."
            )

        except mysql.connector.Error as error:
            if db:
                db.rollback()

            print("Registration database error:", error)

            return render_template(
                "register.html",
                message="Database error. Please try again."
            )

        finally:
            if cursor:
                cursor.close()

            if db and db.is_connected():
                db.close()

    return render_template("register.html")


# =====================================
# LOGIN
# =====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password"], password
            ):

                session.clear()
                session["user_id"] = user["id"]
                session["name"] = user["name"]
                session["role"] = user["role"]

                return redirect(url_for("dashboard"))

            return render_template(
                "login.html",
                message="Invalid email or password."
            )

        except mysql.connector.Error as error:
            print("Login database error:", error)

            return render_template(
                "login.html",
                message="Unable to connect to database."
            )

        finally:
            if cursor:
                cursor.close()

            if db and db.is_connected():
                db.close()

    return render_template("login.html")


# =====================================
# DASHBOARD
# =====================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    return render_template("dashboard.html")


# =====================================
# DONOR: SUBMIT FOOD DONATION
# =====================================

@app.route("/donate", methods=["GET", "POST"])
def donate():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "donor":
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        food_name = request.form["food_name"]
        quantity = request.form["quantity"]
        people_count = request.form["people_count"]
        pickup_address = request.form["pickup_address"]
        expiry_date = request.form["expiry_date"]

        db = None
        cursor = None

        try:
            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO donations (
                    donor_id,
                    food_name,
                    quantity,
                    people_count,
                    pickup_address,
                    expiry_date
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session["user_id"],
                food_name,
                quantity,
                people_count,
                pickup_address,
                expiry_date
            ))

            db.commit()

            return "Food Donation Submitted Successfully!"

        except mysql.connector.Error as error:
            if db:
                db.rollback()

            print("Donation error:", error)
            return "Unable to submit donation. Please try again."

        finally:
            if cursor:
                cursor.close()

            if db and db.is_connected():
                db.close()

    return render_template("donate.html")


# =====================================
# NGO: VIEW AVAILABLE DONATIONS
# =====================================

@app.route("/ngo-donations")
def ngo_donations():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("dashboard"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                d.id,
                d.food_name,
                d.quantity,
                d.people_count,
                d.pickup_address,
                d.expiry_date,
                d.created_at,
                d.status,
                u.name AS donor_name
            FROM donations d
            JOIN users u ON d.donor_id = u.id
            WHERE d.status = 'Available'
            ORDER BY d.created_at DESC
        """)

        donations = cursor.fetchall()

    except mysql.connector.Error as error:
        print("NGO donations error:", error)
        return "Unable to load donations. Please try again."

    finally:
        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()

    return render_template(
        "ngo_donations.html",
        donations=donations
    )


# =====================================
# NGO: ACCEPT DONATION
# =====================================

@app.route("/accept-donation/<int:donation_id>", methods=["POST"])
def accept_donation(donation_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("dashboard"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE donations
            SET
                status = 'Accepted',
                accepted_by = %s,
                accepted_at = NOW()
            WHERE id = %s
            AND status = 'Available'
        """, (
            session["user_id"],
            donation_id
        ))

        db.commit()

        if cursor.rowcount == 0:
            return "Donation already accepted or not available."

    except mysql.connector.Error as error:
        if db:
            db.rollback()

        print("Accept donation error:", error)
        return "Unable to accept donation. Please try again."

    finally:
        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()

    return redirect(url_for("ngo_donations"))


# =====================================
# DONOR: TRACK MY DONATIONS
# =====================================

@app.route("/my-donations")
def my_donations():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "donor":
        return redirect(url_for("dashboard"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                d.id,
                d.food_name,
                d.quantity,
                d.people_count,
                d.pickup_address,
                d.expiry_date,
                d.status,
                d.accepted_at,
                u.name AS ngo_name
            FROM donations d
            LEFT JOIN users u
                ON d.accepted_by = u.id
            WHERE d.donor_id = %s
            ORDER BY d.created_at DESC
        """, (session["user_id"],))

        donations = cursor.fetchall()

    except mysql.connector.Error as error:
        print("Tracking error:", error)
        return "Unable to load your donations."

    finally:
        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()

    return render_template(
        "donor_donations.html",
        donations=donations
    )


# =====================================
# NGO: MY ACCEPTED DONATIONS
# =====================================

@app.route("/my-accepted-donations")
def my_accepted_donations():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("dashboard"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                d.id,
                d.food_name,
                d.quantity,
                d.people_count,
                d.pickup_address,
                d.expiry_date,
                d.accepted_at,
                u.name AS donor_name
            FROM donations d
            JOIN users u ON d.donor_id = u.id
            WHERE d.accepted_by = %s
            ORDER BY d.accepted_at DESC
        """, (session["user_id"],))

        donations = cursor.fetchall()

    except mysql.connector.Error as error:
        print("Accepted donations error:", error)
        return "Unable to load accepted donations."

    finally:
        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()

    return render_template(
        "ngo_accepted_donations.html",
        donations=donations
    )


# =====================================
# ADMIN DASHBOARD
# =====================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                COUNT(*) AS total_users,
                SUM(role = 'donor') AS total_donors,
                SUM(role = 'ngo') AS total_ngos,
                SUM(role = 'admin') AS total_admins
            FROM users
        """)

        user_stats = cursor.fetchone()

        cursor.execute("""
            SELECT
                COUNT(*) AS total_donations,
                SUM(status = 'Available') AS available_donations,
                SUM(status = 'Accepted') AS accepted_donations
            FROM donations
        """)

        donation_stats = cursor.fetchone()

    except mysql.connector.Error as error:
        print("Admin dashboard error:", error)
        return "Unable to load admin dashboard."

    finally:
        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()

    return render_template(
        "admin_dashboard.html",
        user_stats=user_stats,
        donation_stats=donation_stats
    )


# =====================================
# LOGOUT
# =====================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))  

@app.route("/ngo-matches/<int:donation_id>")
def ngo_matches(donation_id):

    if "user_id" not in session or session.get("role") != "donor":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM donations
        WHERE id = %s AND donor_id = %s
    """, (donation_id, session["user_id"]))

    donation = cursor.fetchone()

    if not donation:
        cursor.close()
        conn.close()
        return "Donation not found", 404

    cursor.execute("""
        SELECT id, name, address, capacity_people,
               food_requirements
        FROM users
        WHERE role = 'ngo'
    """)

    ngos = cursor.fetchall()

    matches = []

    for ngo in ngos:
        score = 0
        reasons = []

        requirements = (ngo["food_requirements"] or "").lower()
        food_name = donation["food_name"].lower()

        if food_name in requirements:
            score += 50
            reasons.append("Food requirement matched")

        capacity = ngo["capacity_people"] or 0

        if capacity >= (donation["people_count"] or 0):
            score += 50
            reasons.append("Sufficient NGO capacity")

        if score > 0:
            matches.append({
                "name": ngo["name"],
                "address": ngo["address"],
                "score": score,
                "reasons": reasons
            })

    matches.sort(key=lambda x: x["score"], reverse=True)

    cursor.close()
    conn.close()

    return render_template(
        "ngo_matches.html",
        donation=donation,
        matches=matches
    )


# =====================================
# RUN FLASK APPLICATION
# =====================================

if __name__ == "__main__":
    app.run(debug=True)
