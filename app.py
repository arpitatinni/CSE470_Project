from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from models import *
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

init_app(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        logger.debug("Received POST request for login")
        logger.debug(f"Form data: {request.form}")
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.debug(f"Parsed form data - username: {username}")
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session[username] = username
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('getDashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        logger.debug("Received POST request for signup")
        logger.debug(f"Form data: {request.form}")
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        address = request.form.get('address')
        trole = request.form.get('role')
        role = trole.split(' - ')[0]
        
        logger.debug(f"Parsed form data - username: {username}, email: {email}, role: {role}")
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('signup'))
        
        try:
            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password)
            logger.debug(f"Created new user object: {new_user.username}")
            
            db.session.add(new_user)
            db.session.commit()
            logger.debug("Successfully added user to database")
            if new_user.role == 'restaurant':
                restaurant = Restaurant(user_id=new_user.id, address=address, name=username)
                db.session.add(restaurant)
            elif new_user.role == 'ngo':
                ngo = NGO(user_id=new_user.id, name=username, service_area=address, focus_area=trole.split(' - ')[1])
                db.session.add(ngo)
            elif new_user.role == 'volunteer':
                volunteer = Volunteer(user_id=new_user.id, service_area=address)
                db.session.add(volunteer)
            db.session.commit()

            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')


@app.route('/dashboard')
def getDashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session['role'] == 'restaurant':
        return redirect(url_for('restaurant'))
    if session['role'] == 'ngo':
        return redirect(url_for('ngo'))
    if session['role'] == 'volunteer':
        return redirect(url_for('volunteer'))

""" Restaurant Dashboard Area """
@app.route('/dashboard/restaurant', methods=['GET', 'POST'])
def restaurant():
    if session.get('role')=='restaurant':
        if request.method == 'POST':
            restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
            donation = Donation(
                user_id=session['user_id'],
                description=request.form['description'],
                quantity=request.form['quantity'],
                restaurant_id=restaurant.id,
                preference=request.form['preference'],
                expiry_date=request.form['expiry_date']
            )
            db.session.add(donation)
            db.session.commit()
            flash('Donation created successfully')
            return redirect(url_for('getDashboard'))

        elif request.method == 'GET':
            donations = Donation.query.filter_by(user_id=session['user_id']).order_by(Donation.expiry_date.desc()).all()
            return render_template('restaurant.html', donations=donations, acceptedby=acceptedby)

    else:
        return redirect(url_for('getDashboard'))




@app.route('/cancel_donation/<int:donation_id>')
def cancel_donation(donation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user.role != 'restaurant':
        flash('Only restaurants can cancel donations')
        return redirect(url_for('index'))

    donation = Donation.query.get_or_404(donation_id)
    
    if donation.user_id != session['user_id']:
        flash('You can only cancel your own donations')
        return redirect(url_for('restaurant'))
    
    if donation.status != 'pending':
        flash('You can only cancel pending donations')
        return redirect(url_for('restaurant'))

    db.session.delete(donation)
    db.session.commit()
    flash('Donation cancelled successfully')
    return redirect(url_for('restaurant'))


def acceptedby(donation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    donation = Donation.query.get_or_404(donation_id)
    ngo_id = donation.status.split(',')[1]
    ngo = NGO.query.filter(NGO.id == ngo_id).first()
    return ngo.name


@app.route('/dashboard/ngo', methods=['GET', 'POST'])
def ngo():
    if session.get('role')=='ngo':
        if request.method == 'GET':
            ngo = NGO.query.filter_by(user_id=session['user_id']).first()
            
            available_donations = Donation.query.filter(
                (Donation.status == 'pending') &
                (Donation.preference == ngo.focus_area) &
                (Donation.restaurant.has(address=ngo.service_area))
            ).order_by(Donation.expiry_date.desc()).all()
            past_donations = Donation.query.filter(
                (Donation.status.like(f'accepted,{ngo.id},%')) | 
                (Donation.status.like(f'delivered,{ngo.id},%'))
            ).order_by(Donation.expiry_date.desc()).all()
            return render_template('ngo.html', donations=available_donations, past_donations=past_donations, acceptedby=acceptedby, getRestaurant=getRestaurant)
    else:
            return render_template('ngo.html')


@app.route('/choose_volunteer/<int:donation_id>', methods=['GET'])
def choose_volunteer(donation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] != 'ngo':
        flash('Only NGOs can choose volunteers')
        return redirect(url_for('index'))
    ngo = NGO.query.filter_by(user_id=session['user_id']).first()
    donation = Donation.query.get_or_404(donation_id)
    address = Restaurant.query.filter_by(id=donation.restaurant_id).first().address
    volunteer = Volunteer.query.filter(Volunteer.service_area.like(f'%{address}%'))
    volunteers = volunteer.all()
    return render_template('volunteers.html', volunteers=volunteers, donation=donation, getVolunteerName=getVolunteerName)


def getVolunteerName(id):
    return User.query.filter_by(id=id).first().username

@app.route('/accept_donation/<int:donation_id>/<int:volunteer_id>')
def accept_donation(donation_id, volunteer_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
   
    if session['role'] != 'ngo':
        flash('Only NGOs can accept donations', 'danger')
        return redirect(url_for('index'))
    ngo = NGO.query.filter_by(user_id=session['user_id']).first()
    donation = Donation.query.get_or_404(donation_id)
    donation.status = f'accepted,{ngo.id},{volunteer_id}'
    db.session.commit()
    flash('Donation accepted successfully', 'success')
    return redirect(url_for('ngo'))

def getRestaurant(id):
    return Restaurant.query.filter_by(id=id).first()




@app.route('/dashboard/volunteer', methods=['GET', 'POST'])
def volunteer():
    if session.get('role')=='volunteer':
        if request.method == 'GET':
            volunteer = Volunteer.query.filter_by(user_id=session['user_id']).first()
            available_donations = Donation.query.filter(
                Donation.status.like(f'accepted,%')
            ).filter(
                Donation.status.like(f'%,{volunteer.id}')
            ).order_by(Donation.expiry_date.desc()).all()

            past_donations = Donation.query.filter(
                Donation.status.like(f'delivered,%')
            ).filter(
                Donation.status.like(f'%,{volunteer.id}')
            ).order_by(Donation.expiry_date.desc()).all()
            return render_template('volunteer.html', donations=available_donations, past_donations=past_donations, acceptedby=acceptedby, getRestaurant=getRestaurant)
    else:
            return render_template('volunteer.html')


@app.route('/deliver_donation/<int:donation_id>', methods=['POST'])
def deliver_donation(donation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['role'] != 'volunteer':
        flash('Only volunteers can deliver donations', 'warning')
        return redirect(url_for('index'))
    volunteer = Volunteer.query.filter_by(user_id=session['user_id']).first()
    donation = Donation.query.get_or_404(donation_id)
    photo = request.files['proof']
    feedback = request.form['feedback']
    proof = DeliveryProof(donation_id=donation_id, photo=photo.read(), feedback=feedback)
    db.session.add(proof)
    restaurant = donation.status.split(',')[1]
    donation.status = f'delivered,{restaurant},{volunteer.id}'
    db.session.commit()
    flash('Donation delivered successfully', 'success')
    return redirect(url_for('volunteer'))



@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'GET':
        if user.role == 'restaurant':
            restaurant = Restaurant.query.filter_by(user_id=user.id).first()
            return render_template('profile.html', User=user, Restaurant=restaurant, address=restaurant.address, getTotalDonation=getTotalDonation)
        if user.role == 'ngo':
            ngo = NGO.query.filter_by(user_id=user.id).first()
            return render_template('profile.html', User=user, Ngo=ngo, address=ngo.service_area, getTotalDonation=getTotalDonation)
        if user.role == 'volunteer':
            volunteer = Volunteer.query.filter_by(user_id=user.id).first()
            return render_template('profile.html', User=user, Volunteer=volunteer, address=volunteer.service_area, getTotalDonation=getTotalDonation) 
    if request.method == 'POST':
        if user.role == 'restaurant':
            restaurant = Restaurant.query.filter_by(user_id=user.id).first()
            user.username = request.form['username']
            restaurant.address = request.form['address']
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile'))
        if user.role == 'ngo':
            ngo = NGO.query.filter_by(user_id=user.id).first()
            user.username = request.form['username']
            ngo.service_area = request.form['address']
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile'))
        if user.role == 'volunteer':
            volunteer = Volunteer.query.filter_by(user_id=user.id).first()
            user.username = request.form['username']
            volunteer.service_area = request.form['address']
            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile'))
    
    
@app.route('/profile/<role>/<int:id>', methods=['GET'])
def getProfile(role, id):
    if role == 'restaurant':
        restaurant = Restaurant.query.filter_by(id=id).first()
        user = User.query.filter_by(id=restaurant.user_id).first()
        return render_template('profile.html', User=user, public=True, address=restaurant.address, getTotalDonation=getTotalDonation)
    if role == 'ngo':
        ngo = NGO.query.filter_by(id=id).first()
        user = User.query.filter_by(id=ngo.user_id).first()
        return render_template('profile.html', User=user, public=True, address=ngo.service_area, getTotalDonation=getTotalDonation)
    if role == 'volunteer':
        volunteer = Volunteer.query.filter_by(id=id).first()
        user = User.query.filter_by(id=volunteer.user_id).first()
        return render_template('profile.html', User=user, public=True, address=volunteer.service_area, getTotalDonation=getTotalDonation)


def getTotalDonation(id):
    user = User.query.get(id)
    if user.role == 'restaurant':
        return Donation.query.filter_by(user_id=user.id).count()
    elif user.role == 'ngo':
        ngo = NGO.query.filter_by(user_id=user.id).first()
        past_donations = Donation.query.filter(
            (Donation.status.like(f'accepted,{ngo.id},%')) | 
            (Donation.status.like(f'delivered,{ngo.id},%'))
        ).order_by(Donation.expiry_date.desc()).count()

        return past_donations
    elif user.role == 'volunteer':
        volunteer = Volunteer.query.filter_by(user_id=user.id).first()
        available_donations = Donation.query.filter(
            Donation.status.like(f'accepted,%')
        ).filter(
            Donation.status.like(f'%,{volunteer.id}')
        ).order_by(Donation.expiry_date.desc()).count()

        past_donations = Donation.query.filter(
            Donation.status.like(f'delivered,%')
        ).filter(
            Donation.status.like(f'%,{volunteer.id}')
        ).order_by(Donation.expiry_date.desc()).count()
        return available_donations + past_donations
        



@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=6969)