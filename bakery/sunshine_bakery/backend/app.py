import datetime
from flask import Flask, request, jsonify, abort, g, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_cors import CORS
from functools import wraps
from flask_jwt_extended import JWTManager, get_jwt_identity
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost/sunshine_bakery'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['JWT_SECRET_KEY'] = 'replace_this_with_your_secret_key'  # Change this to a secure random key
CORS(app)  # Enable CORS for all routes
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    availability = db.Column(db.Boolean, default=True)  # Adjust data type as per your database schema

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'availability': self.availability
        }
        
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer)
    order_items = db.Column(db.Text)  # Store as JSON string

    def __repr__(self):
        return f"<Order {self.id}>"

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'message': self.message,
            'created_at': self.created_at
        }   
    
class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at
        }
    
class Prebooking(db.Model):
    __tablename__ = 'prebookings'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    item_name = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    special_requests = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
@app.route('/api/contact_messages', methods=['POST'])
def create_contact_message():
    data = request.json
    new_message = ContactMessage(
        name=data['name'],
        email=data['email'],
        message=data['message']
    )
    db.session.add(new_message)
    db.session.commit()
    return jsonify(new_message.to_dict()), 201

@app.route('/api/contact_messages', methods=['GET'])
def get_contact_messages():
    messages = ContactMessage.query.all()
    return jsonify([message.to_dict() for message in messages])

@app.route('/api/admin/contact_messages', methods=['GET'])
def get_contact_message():
    messages = ContactMessage.query.all()
    return jsonify([message.to_dict() for message in messages])

@app.route('/api/admin/contact_messages/<int:id>', methods=['DELETE'])
def delete_contact_message(id):
    message = ContactMessage.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    return jsonify({'message': 'Message deleted successfully'})

        
# Utility function to check admin role
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_jwt_identity()
        if not current_user or current_user['role'] != 'admin':
            return jsonify({'message': 'Access forbidden: Admins only'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    if not all([username, password, role]):
        return jsonify({'message': 'All fields are required!'}), 400

    new_user = User(username=username, password=password, role=role)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    user = User.query.filter_by(username=username, password=password).first()

    if user:
        return jsonify({'message': 'Login successful', 'role': user.role})
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/api/menu', methods=['GET'])
def get_menu():
    menu_items = MenuItem.query.all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': str(item.price),
        'availability': item.availability
    } for item in menu_items])

@app.route('/api/user/menu', methods=['GET'])
def get_user_menu():
    menu_items = MenuItem.query.all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': str(item.price),
        'availability':item.availability
    } for item in menu_items])

@app.route('/api/admin/menu', methods=['GET'])
def get_admin_menu_items():
    try:
        menu_items = MenuItem.query.all()
        serialized_menu = [item.serialize() for item in menu_items]
        return jsonify(serialized_menu), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/menu', methods=['POST'])
def add_menu_item():
    try:
        new_item_data = request.json
        new_item = MenuItem(
            name=new_item_data['name'],
            description=new_item_data.get('description', ''),
            price=float(new_item_data['price']),
            availability=new_item_data.get('availability', True)  # Assuming default availability is True
        )
        db.session.add(new_item)
        db.session.commit()
        return jsonify({'message': 'Menu item added successfully'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Menu item already exists'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/menu/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    try:
        item = MenuItem.query.get(item_id)
        if not item:
            return jsonify({'error': 'Menu item not found'}), 404

        data = request.json
        item.name = data.get('name', item.name)
        item.description = data.get('description', item.description)
        item.price = float(data.get('price', item.price))
        item.availability = data.get('availability', item.availability)

        db.session.commit()
        return jsonify({'message': 'Menu item updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    try:
        item = MenuItem.query.get(item_id)
        if not item:
            return jsonify({'error': 'Menu item not found'}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Menu item deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    app.logger.info(f"Received data: {data}")

    if not data:
        app.logger.error('No data provided')
        return jsonify({'error': 'No data provided'}), 400

    order_items = data.get('items')

    if not order_items:
        app.logger.error('Missing order_items')
        return jsonify({'error': 'Missing order_items'}), 400

    try:
        quantity = sum(item.get('quantity', 0) for item in order_items)
        total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in order_items)
    except Exception as e:
        app.logger.error(f"Data processing error: {e}")
        return jsonify({'error': 'Invalid data format'}), 400

    new_order = Order(
        total_amount=total_amount,
        quantity=quantity,
        order_items=str(order_items)  # Convert list to string for storage
    )
    db.session.add(new_order)
    db.session.commit()

    return jsonify({'message': 'Order placed successfully'}), 201

@app.route('/api/admin/orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()
    orders_list = [
        {
            'id': order.id,
            'order_date': order.order_date,
            'total_amount': str(order.total_amount),
            'quantity': order.quantity,
            'order_items': order.order_items
        }
        for order in orders
    ]
    return jsonify(orders_list)

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        comment = data.get('comment')
        rating = data.get('rating')

        if not username or not email or not comment or not rating:
            return jsonify({'error': 'Missing required fields'}), 400

        feedback = Feedback(username=username, email=email, comment=comment, rating=rating)
        db.session.add(feedback)
        db.session.commit()

        return jsonify(feedback.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error adding feedback: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/api/feedback', methods=['GET'])
def get_feedbacks():
    try:
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        return jsonify([feedback.to_dict() for feedback in feedbacks])
    except Exception as e:
        print(f"Error fetching feedbacks: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/api/admin/feedback', methods=['GET'])
def get_admin_feedbacks():
    feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return jsonify([feedback.to_dict() for feedback in feedbacks])

# Route to create a prebooking
@app.route('/api/prebookings', methods=['POST'])
def create_prebooking():
    data = request.json
    new_prebooking = Prebooking(
        username=data['username'],
        email=data['email'],
        phone=data['phone'],
        item_name=data['item_name'],
        quantity=data['quantity'],
        special_requests=data.get('special_requests'),
        date=data['date'],
        time=data['time'],
        comment=data.get('comment')
    )
    db.session.add(new_prebooking)
    db.session.commit()
    return jsonify({'message': 'Prebooking created successfully!'}), 201

# Route to get all prebookings (admin)
@app.route('/api/admin/prebookings', methods=['GET'])
def get_prebookings():
    prebookings = Prebooking.query.all()
    prebooking_list = [
        {
            'id': pb.id,
            'username': pb.username,
            'email': pb.email,
            'phone': pb.phone,
            'item_name': pb.item_name,
            'quantity': pb.quantity,
            'special_requests': pb.special_requests,
            'date': pb.date.strftime('%Y-%m-%d'),
            'time': pb.time.strftime('%H:%M'),
            'comment': pb.comment,
            'created_at': pb.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for pb in prebookings
    ]
    return jsonify(prebooking_list), 200

@app.route('/api/menu_items', methods=['GET'])
def get_menu_items():
    menu_items = MenuItem.query.filter_by(availability=True).all()
    menu_list = [
        {
            'id': item.id,
            'name': item.name,
            'price': float(item.price)
        }
        for item in menu_items
    ]
    return jsonify(menu_list), 200

@app.route('/api/user', methods=['GET'])
def get_user():
    # Example implementation
    username = request.args.get('username')  # Assuming username is passed as a query parameter
    if not username:
        return jsonify({'error': 'Username not provided'}), 400
    
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'username': user.username,
        'role': user.role,
        'email': user.email
    })
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
