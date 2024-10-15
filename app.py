import os
import sqlite3
import stripe
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin
from flask_mail import Mail

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Flask-Login configuration
login_manager = LoginManager(app)


# User loader
class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE customer_id=?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    return User(user_row[0], user_row[1], user_row[2]) if user_row else None


# Database initialization
def init_db():
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            flight_id INTEGER PRIMARY KEY,
            origin TEXT,
            destination TEXT,
            date TEXT,
            seats_available INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id INTEGER PRIMARY KEY,
            flight_id INTEGER,
            customer_id INTEGER,
            FOREIGN KEY (flight_id) REFERENCES flights (flight_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY,
            reservation_id INTEGER,
            amount REAL,
            status TEXT,
            FOREIGN KEY (reservation_id) REFERENCES reservations (reservation_id)
        )
    ''')
    conn.commit()
    conn.close()


# Function to add an assortment of flights to the database
def add_flights():
    flights_data = [
        ('New York', 'Los Angeles', '2024-11-11', 100),
        ('Chicago', 'Miami', '2024-12-12', 50),
        ('San Francisco', 'Las Vegas', '2024-12-13', 75),
        ('Houston', 'Seattle', '2024-12-14', 60),
        ('Denver', 'New York', '2024-12-15', 80),
        ('Boston', 'Chicago', '2024-12-16', 90),
        ('Atlanta', 'Dallas', '2024-12-17', 30),
    ]

    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()

    for flight in flights_data:
        # Check if the flight already exists
        cursor.execute('''
            SELECT COUNT(*) FROM flights
            WHERE origin = ? AND destination = ? AND date = ?
        ''', (flight[0], flight[1], flight[2]))

        exists = cursor.fetchone()[0]

        # Only insert if the flight does not exist
        if exists == 0:
            cursor.execute('''
                INSERT INTO flights (origin, destination, date, seats_available)
                VALUES (?, ?, ?, ?)
            ''', flight)

    conn.commit()
    conn.close()

# Function to delete duplicate flight entries from the database
def delete_duplicate_flights():
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()

    # Create a temporary table to hold unique records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flights_temp AS
        SELECT MIN(rowid) AS rowid, origin, destination, date, seats_available
        FROM flights
        GROUP BY origin, destination, date;
    ''')

    # Delete all records from the original flights table
    cursor.execute('DELETE FROM flights')

    # Insert unique records back into the original flights table
    cursor.execute('''
        INSERT INTO flights (origin, destination, date, seats_available)
        SELECT origin, destination, date, seats_available
        FROM flights_temp;
    ''')

    # Drop the temporary table
    cursor.execute('DROP TABLE flights_temp')

    conn.commit()
    conn.close()

# Function to get available flights based on search criteria
def get_flights(origin, destination, date):
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM flights 
        WHERE origin=? AND destination=? AND date=? AND seats_available > 0
    ''', (origin, destination, date))
    flights = cursor.fetchall()
    conn.close()
    return flights


# Function to check flight status by flight ID
def check_flight_status(flight_id):
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM flights WHERE flight_id=?
    ''', (flight_id,))
    flight = cursor.fetchone()
    conn.close()
    return flight

# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')


# Route for searching flights
def search_database(flight_id=None, origin=None, destination=None, date=None, seats_available=None):
    # Connect to the SQLite database
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()

    # Base SQL query
    query = "SELECT * FROM flights WHERE 1=1"  # The `1=1` is a trick to facilitate appending conditions
    parameters = []

    # Append conditions based on user inputs
    if flight_id:
        query += " AND id = ?"
        parameters.append(flight_id)
    if origin:
        query += " AND origin = ?"
        parameters.append(origin)
    if destination:
        query += " AND destination = ?"
        parameters.append(destination)
    if date:
        query += " AND date = ?"
        parameters.append(date)
    if seats_available:
        query += " AND seats_available >= ?"
        parameters.append(seats_available)

    # Execute the query
    cursor.execute(query, parameters)

    # Fetch all matching records
    flights = cursor.fetchall()

    # Optionally, you could format the results into a list of dictionaries
    results = [{
        'id': flight[0],
        'origin': flight[1],
        'destination': flight[2],
        'date': flight[3],
        'seats_available': flight[4]
    } for flight in flights]

    # Close the cursor and connection
    cursor.close()
    conn.close()

    return results


@app.route('/search_flights', methods=['GET', 'POST'])
def search_flights():
    if request.method == 'POST':
        flight_id = request.form.get('flight_id')
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        date = request.form.get('date')
        seats_available = request.form.get('seats_available')

        # Add your database logic here to fetch flights based on the criteria
        flights = search_database(flight_id, origin, destination, date, seats_available)

        return render_template('search_flights.html', flights=flights)  # Pass the flights to the template
    return render_template('search_flights.html', flights=[])


@app.route('/flight_details/<int:flight_id>', methods=['GET'])
def flight_details(flight_id):
    flight = check_flight_status(flight_id)  # This function fetches flight by ID
    if flight:
        return render_template('flight_details.html', flight=flight)
    else:
        flash('Flight not found.')
        return redirect(url_for('index'))  # Redirect if the flight is not found


# Route to purchase a flight
@app.route('/purchase_flight', methods=['POST'])
def purchase_flight():
    flight_id = request.form['flight_id']
    customer_id = request.form['customer_id']  # Get customer ID from session
    amount = request.form['amount']  # Retrieve the flight price

    # Stripe payment processing
    try:
        charge = stripe.Charge.create(
            amount=int(float(amount) * 100),  # Amount in cents
            currency='usd',
            description='Flight Purchase',
            source=request.form['stripeToken']  # The token generated by Stripe.js
        )
    except stripe.error.StripeError:
        flash('There was a problem with your payment. Please try again.')
        return redirect(url_for('flight_search'))

    # Insert reservation into the database
    conn = sqlite3.connect('airline_reservation.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reservations (flight_id, customer_id) VALUES (?, ?)",
        (flight_id, customer_id)
    )
    reservation_id = cursor.lastrowid

    # Record the payment in the payments table
    cursor.execute(
        "INSERT INTO payments (reservation_id, amount, status) VALUES (?, ?, ?)",
        (reservation_id, amount, charge['status'])
    )

    conn.commit()
    conn.close()

    flash('Purchase successful! Your reservation has been made.')
    return redirect(url_for('flight_search'))  # Redirect to flight search page or reservation page


# Route to check flight status by flight ID
@app.route('/flight_status/<int:flight_id>', methods=['GET'])
def flight_status(flight_id):
    flight = check_flight_status(flight_id)
    if flight:
        return render_template('flight_status.html', flight=flight)
    else:
        flash('Flight not found.')
        return redirect(url_for('index'))


# Main block
if __name__ == '__main__':
    init_db()  # Initialize the database on startup if not already created
    add_flights()  # Add flights to the database
    app.run(debug=True)
