from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Needed for session management

# --- FLASK LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE CONFIGURATION ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Srijan4920',  # <--- Updated with your password
    'database': 'CSE_Project_DB'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- USER CLASS ---
class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Customers WHERE Customer_ID = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['Customer_ID'], name=user_data['Name'], email=user_data['Email'])
    return None

# --- ROUTES ---

@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch Inventory
    cursor.execute("SELECT * FROM view_book_summary")
    books = cursor.fetchall()

    # 2. Fetch ONLY the logged-in user's orders
    cursor.execute("""
        SELECT o.Order_ID, b.Title, o.Order_Date, o.Total_Amount 
        FROM Orders o 
        JOIN Books b ON o.Book_ID = b.Book_ID 
        WHERE o.Customer_ID = %s 
        ORDER BY o.Order_Date DESC
    """, (current_user.id,))
    my_orders = cursor.fetchall()
    
    conn.close()
    return render_template('dashboard.html', books=books, my_orders=my_orders, user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Customers WHERE Email = %s", (email,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and user_data['Password'] and check_password_hash(user_data['Password'], password):
            user_obj = User(id=user_data['Customer_ID'], name=user_data['Name'], email=user_data['Email'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        city = request.form.get('city', '')
        
        hashed_pw = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Customers (Name, Email, Phone, City, Country, Password) VALUES (%s, %s, %s, %s, 'India', %s)",
                           (name, email, phone, city, hashed_pw))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    book_id = request.form['book_id']
    quantity = request.form['quantity']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # We use current_user.id here automatically!
        cursor.callproc('AddNewOrder', [current_user.id, book_id, quantity])
        conn.commit()
        flash("Order placed successfully!", "success")
    except mysql.connector.Error as err:
        flash(f"Error: {err}", "danger")
    finally:
        conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)