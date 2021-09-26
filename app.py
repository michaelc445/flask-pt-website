from flask import Flask,session,render_template,redirect,url_for,g
from database import get_db, close_db
from flask_session import Session
from forms import RegisterForm,LoginForm,TrainingForm,PreferenceForm,TrainerForm,ConfirmPaymentForm,NewActivityForm,DeleteActivityForm,SearchActivityForm,ResetPasswordForm,RequestActivityForm,CancelBookingForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timedelta
import time,json
from functools import wraps
app = Flask(__name__)
app.config["SECRET_KEY"]="This-is-my-secret-key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


"""

I've set up an admin account and trainer account for testing

admin only routes:
/admin - shows information about who has joined the website and all bookings
/new_activity - add new activity to the website for trainers/clients to pick
/remove_activity - removes activity from the website

trainer routes:
/preferences - allows trainers to change the activities they train
/trainer_cancel - allows trainers to cancel future bookings


regular routes (can be used by any account type):
/profile - shows information about future bookings with clients/trainers
/booking - make a booking with a trainer
/request_activity - request new activity to be added to the website
/cancel_booking - cancel future booking with trainer
/register - register new account as trainer/regular
/reset_password
/login
/logout

"""

@app.teardown_appcontext
def close_db_at_end_of_request(e=None):
    close_db(e)


@app.before_request
def load_logged_in_user():
    g.user = session.get("user_id",None)
    g.username = session.get("username",None)

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view


@app.route("/",methods=["GET","POST"])
def home():

    return render_template("index.html")

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm()
    db = get_db()
    if form.validate_on_submit():

        username = form.username.data.lower()
        
        password = form.password.data
        trainer = form.trainer.data
        #check username does not exist
        result = db.execute("""SELECT * FROM users where username = ?""",(username,)).fetchone()

        if result:
            form.username.errors.append("Username already taken")
            return render_template("register.html",form=form)
        else:
            usertype = 0
            if trainer:
                usertype = 1
            db.execute("""INSERT INTO users (username,usertype,password) VALUES (?,?,?)""",(username,usertype,generate_password_hash(password)))
            db.commit()
            return redirect(url_for('login'))
    
    return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm()
    db = get_db()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        #check if username exists
        result = db.execute("""SELECT * FROM users where username = ?""",(username.lower(),)).fetchone()
        if result:
            if check_password_hash(result["password"],password):
                session.clear()
                session["user_id"] = result['user_id']
                session["username"] = result['username']
                session["usertype"]= result['usertype']
                
                return redirect(url_for('profile'))
            else:
                form.password.errors.append("Incorrect password")
                return render_template("login.html",form=form)
        else:
            form.username.errors.append("Invalid username")
            return render_template("login.html",form=form)

    return render_template("login.html",form=form)

@app.route("/logout",methods=["GET","POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for('home'))
    
@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    
    admin=False
    db = get_db()
    if session["usertype"]==2:
        admin=True
    name = session["username"]
    #regular user's schedule
    appointments = db.execute("""select services.activity as session_type,booking_date,user.username as trainer
                                from bookings
                                join users as user on bookings.trainer=user.user_id
                                join services on services.id = bookings.session_type
                                where client = ? and booking_date >= ?""",(session["user_id"],datetime.now())).fetchall()
            
    #getting client list if user is a trainer
    if session["usertype"]==1:
        chosen_dict = db.execute("""select s1.activity as activity,tp.price as price
                                    from services as s1
                                    join trainerPref as tp on tp.activity = s1.id
                                    and tp.trainer_id = ?
                                    where s1.id in (select activity from trainerPref where trainer_id =?)""",(session['user_id'],session['user_id'])).fetchall()
        
        customers =   db.execute("""select services.activity as session_type,booking_date,user.username as client
                                    from bookings
                                    join users as user on bookings.client=user.user_id
                                    join services on services.id = session_type
                                    where trainer = ? and booking_date >= ?""",(session["user_id"],datetime.now())).fetchall()
        #return customer list if user is a trainer
        return render_template("profile.html",name=name,appointments=appointments,customers=customers,chosen_dict=chosen_dict,trainer=True,admin=admin)
            
    
    #return without customer list if user is not a trainer
    return render_template("profile.html",name=name,appointments=appointments,trainer=False,admin=admin)
    
@app.route("/booking",methods=["GET","POST"])
@login_required
def booking():
    form = TrainingForm()
    form2= TrainerForm()
    form3 = ConfirmPaymentForm()
    db= get_db()
    session_choices = db.execute(""" SELECT * from services """).fetchall()
    form.session_type.choices= [(item['id'],item['activity']) for item in session_choices]
    if form.validate_on_submit():
        ##booking_date, booking_time
        bd = form.date.data
        bt = form.time.data
        session_type = form.session_type.data
        print(session_type)
        how_long = form.how_long.data
        #creating new time object to create start/end times
        booking_date = datetime(bd.year,bd.month,bd.day,bt.hour,bt.minute,bt.second)
        now = datetime.now()
        if booking_date <=now:
            form.date.errors.append("Date must be in the future")
            return render_template("booking.html",form=form,form2=form2)
        endtime = booking_date + timedelta(hours=how_long)
        #find out which trainers are free for chosen date/time
        result = db.execute(""" select u1.user_id as user_id,u1.username as username, tp.price as 'price' 
                                from users as u1
                                join trainerPref as tp on tp.trainer_id = u1.user_id and u1.usertype=1 and tp.activity = ? and tp.trainer_id != ?
                                where u1.user_id not in (select trainer from bookings 
                                                 where (booking_date between ? and ?) or (end_time between ? and ?))""",(int(session_type),session['user_id'],booking_date,endtime,booking_date,endtime)).fetchall()
        
        if not result:
            form.time.errors.append("No trainers available at that time")
            return render_template("booking.html",form=form,form2=form2)
        else:
            form2.trainer.choices = [( (item['user_id'],item['price']) ,item['username']+" price: €"+str(item['price'])+"/hr" ) for item in result]
            
        if form2.validate_on_submit():
            #casting the form data back to a tuple didn't work tuple(form2.trainer.data), , this does
            results = form2.trainer.data.split(",")
            results[0]= results[0].replace("(","").replace(" ","")
            results[1]= results[1].replace(")","").replace(" ","")
            selected_trainer = results[0]
            price_from_form = results[1]
            booked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            form3.payment.errors = []
            #confirming price hasn't changed since user was shown trainer/price. maybe unnessecary.
            price = db.execute("""select * from  trainerPref where activity = ? and trainer_id = ?""",(session_type,selected_trainer)).fetchone()['price']
            if int(price_from_form) != price:
                form3.payment.errors.append("The price has changed from"+price_from_form+" to: "+price+" confirm below")
                return render_template("booking.html",form=form,form2=form2,form3=form3,trainer=True,payment=True,payment_message="You must pay: €"+str(price*how_long))
            
            if form3.validate_on_submit():
                
                if form3.payment.data !=price*how_long:
                    form3.payment.errors.append("Thats the wrong price")
                    return render_template("booking.html",form=form,form2=form2,form3=form3,trainer=True,payment=True,payment_message="You must pay: €"+str(price*how_long))
                
                db.execute("""INSERT INTO bookings (trainer,session_type,price,end_time,client,booking_date,booked_at)
                            VALUES (?,?,?,?,?,?,?)""",(selected_trainer,session_type,price,endtime,session['user_id'],booking_date,booked_at))
                db.commit()
                return redirect(url_for('profile'))

            return render_template("booking.html",form=form,form2=form2,form3=form3,trainer=True,payment=True,payment_message="You must pay: €"+str(price*how_long))

        return render_template("booking.html",form=form,form2=form2,form3=form3,trainer=True)
        
    return render_template("booking.html",form=form,form2=form2,form3=form3)

@app.route("/preferences",methods=["GET","POST"])
@login_required
def preferences():
    #if the user isnt a trainer
    if session['usertype']==0:
        return redirect(url_for('profile'))
    
    db = get_db()
    form = PreferenceForm()
    chosen = db.execute("""     select * 
                                from services 
                                where id in (select activity from trainerPref where trainer_id =?)""",(session['user_id'],)).fetchall()
    
    available = db.execute("""  select * 
                                from services 
                                where id not in (select activity from trainerPref where trainer_id =?)""",(session['user_id'],)).fetchall()

    form.available.choices = [("","I dont want to add a service.")]+[(str(item['id']),item['activity']) for item in available]
    form.chosen.choices = [("","I don't want to remove a service.")]+[(str(item['id']),item['activity']) for item in chosen]
    if form.validate_on_submit():
        price = form.price.data
        remove = form.chosen.data
        
        add = form.available.data
        if add !="" and form.price.data ==0:
            form.price.errors.append("This is not a charity website. Add a price.")
            return render_template("preferences.html",form=form)
        #add activities    
        if add != "":
            db.execute("""INSERT INTO trainerPref (trainer_id,activity,price) VALUES (?,?,?) """,(session['user_id'],add,price))
            #moving activity to chosen so it will be there after submt
            for item in form.available.choices:
                if item[0] == add:
                    form.chosen.choices.append(item)
                    form.available.choices.pop(form.available.choices.index(item))
        #remove activities
        if remove !="":
            db.execute("""DELETE FROM trainerPref where trainer_id = ? and activity = ?""",(session['user_id'],remove))
            #removing activity from chosen -> available so it's there after submit
            for item in form.chosen.choices:
                if item[0] == remove:
                    form.available.choices.append(item)
                    form.chosen.choices.pop(form.chosen.choices.index(item))
        
        db.commit()
        form.chosen.data = ""
        form.available.data = ""
        return render_template("preferences.html",form=form)

    return render_template("preferences.html",form=form)

@app.route("/new_activity",methods=["GET","POST"])
@login_required
def new_activity():
    if session['usertype'] != 2:
        return redirect(url_for('profile'))
    db=get_db()
    #get all activities
    all_act = db.execute("SELECT * FROM services").fetchall()
    requested = db.execute("""select * from wanted_act""").fetchall()
    form = NewActivityForm()
    if form.validate_on_submit():
        activity = form.activity.data
        activity = activity.strip(" ")
        #check the item isnt already in the db
        result = db.execute(""" SELECT * FROM SERVICES where activity = ?""",(activity.lower(),)).fetchone()
        if result:
            form.activity.errors.append("This activity already exists")
            return render_template("addActivity.html",form=form,all_act=all_act,requested=requested)
        
        #check is activity in suggestions
        suggested = db.execute("""select * from wanted_act where activity = ?""",(activity,)).fetchone()
        if suggested:
            db.execute("""delete from wanted_act where activity = ?""",(activity,))
            
        db.execute("""INSERT INTO services (activity) VALUES (?)""",(activity.lower(),))
        all_act = db.execute("SELECT * FROM services").fetchall()
        requested = db.execute("""select * from wanted_act""").fetchall()
        db.commit()
        return render_template("addActivity.html",form=form,message="Activity added.",all_act=all_act,requested=requested)
    return render_template("addActivity.html",form=form,message="",all_act=all_act,requested=requested)

@app.route("/remove_activity",methods=["GET","POST"])
@login_required
def remove_activity():
    #user must be admin
    if session['usertype'] != 2:
        return redirect(url_for('profile'))
    db=get_db()
    #get all activities
    all_act = db.execute("SELECT * FROM services").fetchall()
    form = DeleteActivityForm()
    if form.validate_on_submit():
        activity = form.activity.data
        result = db.execute(""" SELECT * FROM SERVICES where activity = ?""",(activity.lower(),)).fetchone()
        if result:
            db.execute("""delete from services where activity = ?""",(activity.lower(),))
            all_act = db.execute("SELECT * FROM services").fetchall()
            db.commit()
            return render_template("deleteActivity.html",form=form,all_act=all_act,message="Activity deleted.")
        
        form.activity.errors.append("We couldn't find that anything with that id number.")
        return render_template("deleteActivity.html",form=form,all_act=all_act)

    return render_template("deleteActivity.html",form=form,all_act=all_act)

@app.route("/reset_password",methods=["GET","POST"])
@login_required
def reset_password():
    form=ResetPasswordForm()
    if form.validate_on_submit():
        old_password = form.old_password.data
        new_password = form.new_password.data
        db = get_db()
        user_details = db.execute("""SELECT * FROM users WHERE user_id =?""",(session['user_id'],)).fetchone()
        if check_password_hash(user_details['password'],old_password):
            db.execute("""UPDATE users SET password = ? where user_id = ?""",(generate_password_hash(new_password),session['user_id']))
            db.commit()
            form.old_password.data = ""
            form.new_password.data = ""
            form.new_password2.data = ""
            return redirect(url_for('login'))
        else:
            form.old_password.errors.append("Incorrect password")
            return render_template("resetPassword.html",form=form)
        
    return render_template("resetPassword.html",form=form)

@app.route("/admin",methods=["GET","POST"])
@login_required
def admin():
    if session['usertype'] != 2:
        return redirect(url_for('profile'))
    db= get_db()
    users = db.execute("select user_id,username,usertype from users;").fetchall()
    
    bookings = db.execute("""  select u1.username as trainer,u2.username as client,s1.activity as activity,b1.booking_date as date
                    from bookings as b1
                    join users as u1 on u1.user_id = b1.trainer
                    join users as u2 on u2.user_id = b1.client
                    join services as s1 on s1.id = b1.session_type;""").fetchall()

    return render_template("admin.html",users=users,bookings=bookings)

@app.route("/request_activity",methods=["GET","POST"])
@login_required
def request_activity():
    form = RequestActivityForm()
    db=get_db()
    if form.validate_on_submit():
        activity = form.activity.data
        #check if activity exists already
        result = db.execute("""select * from services where activity = ?""",(activity,)).fetchone()
        if result:
            form.activity.errors.append("Activity already exists")
            return render_template("requestActivity.html",form=form)
        #check was activity requested
        requested = db.execute("""select * from wanted_act where activity = ? """,(activity,)).fetchone()
        if requested:
            form.activity.errors.append("This has already been requested. Thank you for the suggestion.")
            return render_template("requestActivity.html",form=form)
        #add activity
        db.execute(""" INSERT INTO wanted_act (activity) values (?)""",(activity,))
        db.commit()
        message = "Suggestion added"
        return render_template("requestActivity.html",form=form,message=message)
        
    return render_template("requestActivity.html",form=form)

@app.route("/cancel_booking",methods=["GET","POST"])
@login_required
def cancel_booking():
    user_id = session['user_id']
    form = CancelBookingForm()
    db=get_db()
    bookings = db.execute("""select b1.booking_id as booking_id, b1.booking_date as booking_date,u1.username as trainer,s1.activity as activity
                            from bookings as b1
                            join users as u1 on u1.user_id = b1.trainer
                            join services as s1 on s1.id = b1.session_type
                            where b1.client = ? and b1.booking_date > ?""",(user_id,datetime.now())).fetchall()
    choices = [("","I dont want to cancel anything.")]+[(booking['booking_id'],str(booking['booking_date'])+" trainer: "+str(booking['trainer'])+" Session Type: "+str(booking['activity'])) for booking in bookings]
    form.booking.choices= choices
    if form.validate_on_submit():
        choice = form.booking.data
        db.execute("""delete from bookings where booking_id = ?""",(choice,))
        db.commit()
        #remove booking from form choices
        choices = [("","I dont want to cancel anything.")]+[(booking['booking_id'],str(booking['booking_date'])+" trainer: "+str(booking['trainer'])+" Session Type: "+str(booking['activity'])) for booking in bookings if booking['booking_id'] !=int(choice)]
        form.booking.choices=choices
        return render_template("cancelBooking.html",form=form,message="Booking cancelled. Money may come back, who knows.")

    return render_template("cancelBooking.html",form=form)

@app.route("/trainer_cancel",methods=["GET","POST"])
@login_required
def trainer_cancel():
    if session['usertype'] ==0:
        return redirect(url_for('profile'))
    
    form = CancelBookingForm()
    db = get_db()
    bookings = db.execute("""select b1.booking_id as booking_id, b1.booking_date as booking_date,u1.username as client,s1.activity as activity
                            from bookings as b1
                            join users as u1 on u1.user_id = b1.client
                            join services as s1 on s1.id = b1.session_type
                            where b1.trainer = ? and b1.booking_date > ?""",(session['user_id'],datetime.now())).fetchall()
    choices = [("","I dont want to cancel anything.")]+[(booking['booking_id'],str(booking['booking_date'])+" client: "+str(booking['client'])+" Session Type: "+str(booking['activity'])) for booking in bookings]
    form.booking.choices=choices
    if form.validate_on_submit():
        choice = form.booking.data
        db.execute("""delete from bookings where booking_id = ?""",(choice,))
        db.commit()
        #remove booking from form choices
        choices = [("","I dont want to cancel anything.")]+[(booking['booking_id'],str(booking['booking_date'])+" trainer: "+str(booking['client'])+" Session Type: "+str(booking['activity'])) for booking in bookings if booking['booking_id'] !=int(choice)]
        form.booking.choices=choices
        return render_template("cancelBooking.html",form=form,message="Booking cancelled. You wont be paid for this.")
    return render_template("cancelBooking.html",form=form)
