
from app import get_db_connection
from werkzeug.security import generate_password_hash
from getpass import getpass

name = "Smart Food Rescue"
email = "rescuesmartfood@gmail.com"

phone = input("Enter admin phone number: ")
address = input("Enter admin address: ")

password = getpass("Create admin password: ")
confirm_password = getpass("Confirm admin password: ")

if password != confirm_password:
    print("Passwords do not match!")
    exit()

if len(password) < 8:
    print("Password must be at least 8 characters.")
    exit()

hashed_password = generate_password_hash(password)

db = None
cursor = None

try:
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO users
        (name, email, phone, address, role, password)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        name,
        email,
        phone,
        address,
        "admin",
        hashed_password
    ))

    db.commit()
    print("Admin account created successfully!")

except Exception as error:
    if db:
        db.rollback()

    print("Error:", error)

finally:
    if cursor:
        cursor.close()

    if db and db.is_connected():
        db.close()
