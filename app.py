from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# --- MySQL CONNECTION CONFIGURATION ---
# Format: mysql://username:password@localhost/database_name
# If using pymysql, use: mysql+pymysql://root:your_password@localhost/expense_tracker
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/expense_tracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS and allow cookies/sessions
CORS(app, supports_credentials=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    expenses = db.relationship('Expense', backref='owner', lazy=True)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTHENTICATION ROUTES ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "Username already exists"}), 400
    
    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(username=data['username'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        login_user(user)
        return jsonify({"message": "Logged in successfully"}), 200
    return jsonify({"message": "Invalid username or password"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out"}), 200

# --- EXPENSE LOGIC ---
@app.route('/add', methods=['POST'])
@login_required
def add():
    data = request.json
    new_exp = Expense(
        date=data['date'],
        amount=float(data['amount']),
        category=data['category'],
        description=data['description'],
        user_id=current_user.id
    )
    db.session.add(new_exp)
    db.session.commit()
    return jsonify({"message": "Expense added"}), 201

@app.route('/view', methods=['GET'])
@login_required
def view():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    output = []
    for e in expenses:
        output.append({
            "id": e.id,
            "date": e.date,
            "amount": e.amount,
            "category": e.category,
            "description": e.description
        })
    return jsonify(output)

@app.route('/delete/<int:id>', methods=['DELETE'])
@login_required
def delete(id):
    expense = Expense.query.filter_by(id=id, user_id=current_user.id).first()
    if not expense:
        return jsonify({"message": "Expense not found"}), 404
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"message": "Expense deleted"}), 200

@app.route('/summary', methods=['GET'])
@login_required
def summary():
    results = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).filter(Expense.user_id == current_user.id).group_by(Expense.category).all()
    
    return jsonify({category: total for category, total in results})

if __name__ == "__main__":
    with app.app_context():
        # This creates the tables in your MySQL database
        db.create_all()
    app.run(debug=True)