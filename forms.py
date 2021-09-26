from flask_wtf import FlaskForm
from wtforms import  SubmitField,IntegerField,StringField,PasswordField,BooleanField,DateField,SelectField,RadioField,SelectMultipleField
from wtforms.validators import InputRequired,NumberRange,Length,EqualTo,Regexp
from wtforms.fields.html5 import DateField,TimeField
class LoginForm(FlaskForm):
    username = StringField("username",validators=[InputRequired()])
    password = PasswordField("Password",validators=[InputRequired()])
    submit = SubmitField("Submit")

class RegisterForm(FlaskForm):
    #regex for alphanumeric username from https://stackoverflow.com/a/342977
    username = StringField("Username",validators=[InputRequired(),Length(min=4,max=15),Regexp(regex='^\w+$',message="Alpha Numeric characters only (a-z,A-Z,0-9,_)")])
    password = PasswordField("Password",validators=[InputRequired(),Length(min=8,max=30)])
    password2 = PasswordField("Confirm password",validators=[InputRequired(),Length(min=8,max=30),EqualTo('password')])
    trainer = BooleanField("Are you registering to be a trainer?")
    submit = SubmitField("Submit")

class TrainingForm(FlaskForm):
    date = DateField("What date would you like to book your training session for?",validators=[InputRequired()])
    time = TimeField("What time would you like to book for?",validators=[InputRequired()])
    session_type = SelectField("What type of training session would you like: ",choices=[],validators=[InputRequired()])
    how_long = IntegerField("How many hours would you like to book?",validators=[InputRequired(),NumberRange(1,10,message="Minimum of 1 hour, maximum of 10 hours")])
    submit = SubmitField("submit")

class TrainerForm(FlaskForm):
    trainer = SelectField("Which trainer would you like?",validators=[InputRequired()],choices=[])
    submit = SubmitField("submit")

class PreferenceForm(FlaskForm):
    available = SelectField("Services to add:",choices=[])
    chosen = SelectField("Services to remove:",choices=[])
    price = IntegerField("Price per hour:",default=0)
    submit = SubmitField("Submit")

class ConfirmPaymentForm(FlaskForm):
    payment = IntegerField("Pay here: ",validators=[InputRequired()])
    confirm = BooleanField("I confirm that I am about to send my money away",validators=[InputRequired()],default=False)
    submit = SubmitField("Pay now")

class NewActivityForm(FlaskForm):
    activity = StringField("Enter the new activity here: ",validators=[InputRequired()])
    submit = SubmitField("Add Activity")

class DeleteActivityForm(FlaskForm):
    activity = StringField("What activity would you like to delete?",validators=[InputRequired()])
    confirm = BooleanField("You are about to remove this activity from the website.",validators=[InputRequired()],default=False)
    submit = SubmitField("Delete activity")

class SearchActivityForm(FlaskForm):
    activity = IntegerField("What activity would you like to find?")
    search = SubmitField("Search")

class ResetPasswordForm(FlaskForm):
    old_password = PasswordField("Enter your old password")
    new_password = PasswordField("Enter your new password",validators=[InputRequired(),Length(min=8,max=30)])
    new_password2 = PasswordField("Confirm your new password",validators=[InputRequired(),Length(min=8,max=30),EqualTo('new_password')])
    submit = SubmitField("Submit")

class RequestActivityForm(FlaskForm):
    activity = StringField("What activity would you like to see added to the website?",validators=[InputRequired()])
    submit = SubmitField("Submit")

class CancelBookingForm(FlaskForm):
    booking = SelectField("Which booking would you like to cancel?",validators=[InputRequired()])
    submit = SubmitField("Cancel Booking") 