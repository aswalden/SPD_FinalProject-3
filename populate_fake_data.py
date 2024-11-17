from flask import Flask
from database import (
    create_user, create_resource, create_space, create_event, send_message,
    get_user_by_email, init_db, close_db
)

# Create a Flask app to provide the application context
app = Flask(__name__)
app.config['DATABASE'] = 'smart_neighborhood.db'

def populate_users():
    users = [
        {"name": "Alice Johnson", "email": "alice@example.com", "password": "password123", "location": "Downtown", "profile_image": "alice.jpg"},
        {"name": "Bob Smith", "email": "bob@example.com", "password": "password123", "location": "Uptown", "profile_image": "bob.jpg"},
        {"name": "Carol Lee", "email": "carol@example.com", "password": "password123", "location": "Suburbs", "profile_image": "carol.jpg"},
        {"name": "David Brown", "email": "david@example.com", "password": "password123", "location": "City Center", "profile_image": "david.jpg"},
        {"name": "Eve Davis", "email": "eve@example.com", "password": "password123", "location": "Riverside", "profile_image": "eve.jpg"},
    ]
    for user in users:
        create_user(user["name"], user["email"], user["password"], user["location"], user["profile_image"])

def populate_resources():
    resources = [
        {"user_email": "alice@example.com", "title": "Lawn Mower", "description": "Electric lawn mower, lightly used.", "category": "Tools", "availability": "Available"},
        {"user_email": "bob@example.com", "title": "Bicycle", "description": "Road bike, 21-speed.", "category": "Transport", "availability": "Unavailable"},
        {"user_email": "carol@example.com", "title": "Camping Tent", "description": "2-person camping tent, waterproof.", "category": "Outdoor Gear", "availability": "Available"},
        {"user_email": "david@example.com", "title": "Bookshelf", "description": "Wooden bookshelf, 5 shelves.", "category": "Furniture", "availability": "Available"},
        {"user_email": "eve@example.com", "title": "Piano", "description": "Electric piano, 88 keys.", "category": "Music", "availability": "Unavailable"},
    ]
    for resource in resources:
        user = get_user_by_email(resource["user_email"])
        if user:
            create_resource(user["id"], resource["title"], resource["description"], resource["category"], resource["availability"])

def populate_spaces():
    spaces = [
        {"name": "Community Hall", "description": "Large hall for events.", "location": "Downtown", "availability": "Available", "creator_email": "alice@example.com"},
        {"name": "Meeting Room", "description": "Small meeting room with projector.", "location": "City Center", "availability": "Unavailable", "creator_email": "bob@example.com"},
    ]
    for space in spaces:
        user = get_user_by_email(space["creator_email"])
        if user:
            create_space(space["name"], space["description"], space["location"], space["availability"], user["id"])

def populate_events():
    events = [
        {"name": "Neighborhood Cleanup", "description": "Join us for a community cleanup event.", "date": "2024-11-10", "location": "Park Entrance", "host_email": "carol@example.com"},
        {"name": "Book Club", "description": "Monthly book discussion.", "date": "2024-11-15", "location": "Community Hall", "host_email": "alice@example.com"},
    ]
    for event in events:
        user = get_user_by_email(event["host_email"])
        if user:
            create_event(event["name"], event["description"], event["date"], event["location"], user["id"])

def populate_messages():
    messages = [
        {"sender_email": "alice@example.com", "receiver_email": "bob@example.com", "content": "Hi Bob, is the bicycle available?"},
        {"sender_email": "bob@example.com", "receiver_email": "alice@example.com", "content": "Hi Alice, it's currently not available."},
        {"sender_email": "carol@example.com", "receiver_email": "eve@example.com", "content": "Hi Eve, is the piano still for sale?"},
    ]
    for message in messages:
        sender = get_user_by_email(message["sender_email"])
        receiver = get_user_by_email(message["receiver_email"])
        if sender and receiver:
            send_message(sender["id"], receiver["id"], message["content"])

def main():
    with app.app_context():  # Ensure the application context is active
        init_db()  # Initialize the database
        populate_users()
        populate_resources()
        populate_spaces()
        populate_events()
        populate_messages()
        print("Fake data successfully populated!")
        close_db()  # Close the database connection at the end

if __name__ == "__main__":
    main()
