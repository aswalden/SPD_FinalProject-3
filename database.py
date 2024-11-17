# database.py
import sqlite3
from flask import g
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

DATABASE = 'smart_neighborhood.db'

# Helper functions for database connection
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            location TEXT,
            profile_image TEXT
        );

        CREATE TABLE IF NOT EXISTS resources (
            resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            images TEXT,
            category TEXT,
            availability TEXT,
            date_posted TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            is_system_message INTEGER DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE CASCADE
        );
                         
        CREATE TABLE IF NOT EXISTS spaces (
            space_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            availability TEXT,
            created_by INTEGER NOT NULL,
            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            hosted_by INTEGER NOT NULL,
            FOREIGN KEY (hosted_by) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS resource_bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (resource_id) REFERENCES resources (resource_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS space_bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            space_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (space_id) REFERENCES spaces (space_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS event_bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE CASCADE
        );
    ''')
    db.commit()

# User-related functions
def create_user(name, email, password, location='', profile_image=''):
    db = get_db()
    hashed_password = generate_password_hash(password)
    try:
        db.execute(
            "INSERT INTO users (name, email, password, location, profile_image) VALUES (?, ?, ?, ?, ?)",
            (name, email, hashed_password, location, profile_image)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

def get_user_by_email(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

# Resource-related functions
def create_resource(user_id, title, description, category, availability, image_path):
    db = get_db()
    db.execute(
        "INSERT INTO resources (user_id, title, description, category, availability, date_posted) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (user_id, title, description, category, availability)
    )
    db.commit()

def get_recent_resources(limit=5):
    return get_db().execute(
        "SELECT * FROM resources ORDER BY date_posted DESC LIMIT ?", (limit,)
    ).fetchall()

def get_resource_by_id(resource_id):
    return get_db().execute("SELECT * FROM resources WHERE resource_id = ?", (resource_id,)).fetchone()

def update_resource(resource_id, title, description, category, availability):
    db = get_db()
    db.execute(
        "UPDATE resources SET title = ?, description = ?, category = ?, availability = ? WHERE resource_id = ?",
        (title, description, category, availability, resource_id)
    )
    db.commit()

def delete_resource(resource_id):
    db = get_db()
    db.execute("DELETE FROM resources WHERE resource_id = ?", (resource_id,))
    db.commit()

def get_all_resources():
    return get_db().execute("SELECT * FROM resources").fetchall()

# Review-related functions
def get_top_reviews(limit=5):
    return get_db().execute(
        '''
        SELECT r.*, u.name as reviewer_name
        FROM reviews r
        JOIN users u ON r.reviewer_id = u.id
        ORDER BY r.rating DESC, r.timestamp DESC
        LIMIT ?
        ''', (limit,)
    ).fetchall()

# Message Functions

def get_user_by_id(user_id):
    return get_db().execute(
        "SELECT * FROM users WHERE id = ?", 
        (user_id,)
    ).fetchone()

def send_message(sender_id, receiver_id, content):
    """Send a new message."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (sender_id, receiver_id, content, timestamp)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (sender_id, receiver_id, content)
        )
        conn.commit()
    except Exception as e:
        raise  # Reraise the exception for debugging
    finally:
        conn.close()


def get_inbox(user_id):
    """Retrieve a list of users the current user has conversations with."""
    db = get_db()  # Use Flask's connection manager
    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.id, u.name, MAX(m.timestamp) as last_message
            FROM messages m
            JOIN users u ON u.id = CASE WHEN m.sender_id = ? THEN m.receiver_id ELSE m.sender_id END
            WHERE m.sender_id = ? OR m.receiver_id = ?
            GROUP BY u.id, u.name
            ORDER BY last_message DESC
        """, (user_id, user_id, user_id))
        conversations = cursor.fetchall()
        return conversations
    except Exception as e:
        raise  # Let the exception bubble up for better error logging



def get_conversation(sender_id, receiver_id):
    """Retrieve messages exchanged between two users."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, u.name AS sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.timestamp
        """, (sender_id, receiver_id, receiver_id, sender_id))
        messages = cursor.fetchall()
        return messages
    except Exception as e:
        raise
    finally:
        conn.close()


# events and spaces
# database.py

def create_space(name, description, location, availability, created_by):
    db = get_db()
    db.execute(
        "INSERT INTO spaces (name, description, location, availability, created_by) VALUES (?, ?, ?, ?, ?)",
        (name, description, location, availability, created_by)
    )
    db.commit()

def get_all_spaces():
    return get_db().execute("SELECT * FROM spaces").fetchall()

def get_space_by_id(space_id):
    return get_db().execute("SELECT * FROM spaces WHERE space_id = ?", (space_id,)).fetchone()

def create_event(name, description, date, location, hosted_by):
    db = get_db()
    db.execute(
        "INSERT INTO events (name, description, date, location, hosted_by) VALUES (?, ?, ?, ?, ?)",
        (name, description, date, location, hosted_by)
    )
    db.commit()

def get_all_events():
    return get_db().execute("SELECT * FROM events").fetchall()

def get_event_by_id(event_id):
    return get_db().execute("SELECT event_id, name, description, date, location FROM events WHERE event_id = ?", (event_id,)).fetchone()

def get_resources_by_user(user_id):
    """
    Retrieve all resources created by a specific user.
    """
    return get_db().execute(
        "SELECT * FROM resources WHERE user_id = ?", 
        (user_id,)
    ).fetchall()

def get_events_by_user(user_id):
    """
    Retrieve all events organized by a specific user.
    """
    return get_db().execute(
        "SELECT * FROM events WHERE hosted_by = ?", 
        (user_id,)
    ).fetchall()

def get_spaces_by_user(user_id):
    """
    Retrieve all spaces managed by a specific user.
    """
    return get_db().execute(
        "SELECT * FROM spaces WHERE created_by = ?", 
        (user_id,)
    ).fetchall()

# Resource booking functions
def book_resource(user_id, resource_id, booking_date):
    db = get_db()
    try:
        print(f"Attempting to book resource: user_id={user_id}, resource_id={resource_id}, booking_date={booking_date}")
        db.execute(
            "INSERT INTO resource_bookings (user_id, resource_id, booking_date) VALUES (?, ?, ?)",
            (user_id, resource_id, booking_date)
        )
        db.commit()
        print(f"Booking successful for user_id={user_id}, resource_id={resource_id}.")
    except sqlite3.IntegrityError as e:
        print(f"Integrity error in book_resource: {e}")
        raise Exception(f"Integrity error in book_resource: {e}")
    except Exception as e:
        print(f"Unexpected error in book_resource: {e}")
        raise Exception(f"Unexpected error in book_resource: {e}")


def get_resource_bookings_by_user(user_id):
    return get_db().execute(
        "SELECT rb.*, r.title FROM resource_bookings rb JOIN resources r ON rb.resource_id = r.resource_id WHERE rb.user_id = ?",
        (user_id,)
    ).fetchall()

# Space booking functions
def book_space(user_id, space_id, booking_date):
    db = get_db()
    try:
        print(f"Attempting to book space: user_id={user_id}, space_id={space_id}, booking_date={booking_date}")
        db.execute(
            "INSERT INTO space_bookings (user_id, space_id, booking_date) VALUES (?, ?, ?)",
            (user_id, space_id, booking_date)
        )
        db.commit()
        print(f"Booking successful for user_id={user_id}, space_id={space_id}.")
    except sqlite3.IntegrityError as e:
        print(f"Integrity error in book_space: {e}")
        raise Exception(f"Integrity error in book_space: {e}")
    except Exception as e:
        print(f"Unexpected error in book_space: {e}")
        raise Exception(f"Unexpected error in book_space: {e}")


def get_space_bookings_by_user(user_id):
    return get_db().execute(
        "SELECT sb.*, s.name FROM space_bookings sb JOIN spaces s ON sb.space_id = s.space_id WHERE sb.user_id = ?",
        (user_id,)
    ).fetchall()

def book_event(user_id, event_id, booking_date):
    db = get_db()
    try:
        print(f"Attempting to book event: user_id={user_id}, event_id={event_id}, booking_date={booking_date}")
        db.execute(
            "INSERT INTO event_bookings (user_id, event_id, booking_date) VALUES (?, ?, ?)",
            (user_id, event_id, booking_date)
        )
        db.commit()
        print(f"Booking successful for user_id={user_id}, event_id={event_id}.")
    except sqlite3.IntegrityError as e:
        print(f"Integrity error in book_event: {e}")
        raise Exception(f"Integrity error in book_event: {e}")
    except Exception as e:
        print(f"Unexpected error in book_event: {e}")
        raise Exception(f"Unexpected error in book_event: {e}")


def get_event_bookings_by_user(user_id):
    return get_db().execute(
        "SELECT eb.*, e.name FROM event_bookings eb JOIN events e ON eb.event_id = e.event_id WHERE eb.user_id = ?",
        (user_id,)
    ).fetchall()


def send_system_message(receiver_id, content):
    try:
        print(f"Sending system message to user_id={receiver_id}: {content}")
        db = get_db()
        db.execute(
            """
            INSERT INTO messages (sender_id, receiver_id, content, timestamp, is_system_message)
            VALUES (NULL, ?, ?, datetime('now'), 1)
            """,
            (receiver_id, content)
        )
        db.commit()
        print(f"Message sent to user_id={receiver_id}: {content}")
    except Exception as e:
        print(f"Error sending message: {e}")



def check_upcoming_bookings():
    db = get_db()
    current_date = datetime.now().strftime('%Y-%m-%d')

    try:
        # Debugging: Print current date
        print(f"Current Date: {current_date}")

        # Check all future resource bookings
        resources = db.execute("""
            SELECT rb.user_id, r.title, rb.booking_date
            FROM resource_bookings rb
            JOIN resources r ON rb.resource_id = r.resource_id
            WHERE rb.booking_date >= ?
        """, (current_date,)).fetchall()

        print(f"Resource bookings found: {len(resources)}")  # Debugging
        for resource in resources:
            print(f"Sending message for resource booking: {resource['title']} on {resource['booking_date']}")  # Debugging
            send_system_message(
                receiver_id=resource['user_id'],
                content=f"Reminder: Your resource booking '{resource['title']}' is scheduled for {resource['booking_date']}."
            )

        # Check all future space bookings
        spaces = db.execute("""
            SELECT sb.user_id, s.name, sb.booking_date
            FROM space_bookings sb
            JOIN spaces s ON sb.space_id = s.space_id
            WHERE sb.booking_date >= ?
        """, (current_date,)).fetchall()

        print(f"Space bookings found: {len(spaces)}")  # Debugging
        for space in spaces:
            print(f"Sending message for space booking: {space['name']} on {space['booking_date']}")  # Debugging
            send_system_message(
                receiver_id=space['user_id'],
                content=f"Reminder: Your space booking '{space['name']}' is scheduled for {space['booking_date']}."
            )

        # Check all future event bookings
        events = db.execute("""
            SELECT eb.user_id, e.name, e.date
            FROM event_bookings eb
            JOIN events e ON eb.event_id = e.event_id
            WHERE e.date >= ?
        """, (current_date,)).fetchall()

        print(f"Event bookings found: {len(events)}")  # Debugging
        for event in events:
            print(f"Sending message for event booking: {event['name']} on {event['date']}")  # Debugging
            send_system_message(
                receiver_id=event['user_id'],
                content=f"Reminder: Your event '{event['name']}' is scheduled for {event['date']}."
            )

    except Exception as e:
        print(f"Error checking upcoming bookings: {e}")
        raise

def get_top_users(limit=5):
    """Fetch top-rated users."""
    return get_db().execute(
        """
        SELECT id, name, email, profile_image, rating
        FROM users
        WHERE rating IS NOT NULL
        ORDER BY rating DESC, id ASC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()
