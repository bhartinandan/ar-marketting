from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from photo_frame.models import *

#############################################################
################# Client Forms ##############################
#############################################################

class LoginForm(forms.Form):
    username = forms.CharField(max_length=63,widget=forms.TextInput(attrs={'placeholder': 'Mobile number'}))
    password = forms.CharField(max_length=63,widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    next = forms.CharField(widget=forms.HiddenInput(), required=False)

class SignupuserForm(forms.Form):
    username = forms.CharField(max_length=63,
                               widget=forms.TextInput(attrs={'placeholder': 'Mobile number', 'class':'form-control','aria-label':'.form-select-sm example'})
                                             )

class UserotpForm(forms.Form):
    otp = forms.CharField(max_length=4,
				 min_length=4,
				 widget=forms.NumberInput(attrs={'placeholder': 'otp'}),
			error_messages={"required": "Please enter your otp"})
	
class PasswordForm(forms.Form):
    password = forms.CharField(max_length=63,widget=forms.PasswordInput(attrs={'placeholder': 'password'}))
    