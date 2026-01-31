from django import forms
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class UserCreationForm(BaseUserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, initial='CASHIER')
    phone = forms.CharField(max_length=20, required=False)
    shop_name = forms.CharField(max_length=100, required=False, help_text="Business/Shop name (required for Shop Admin)")
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'shop_name', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class UserUpdateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    phone = forms.CharField(max_length=20, required=False)
    is_active = forms.BooleanField(required=False)
    shop_name = forms.CharField(max_length=100, required=False, help_text="Business/Shop name (required for Shop Admin)")
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'shop_name', 'is_active')
        widgets = {
            'is_active': forms.CheckboxInput(),
        }

class CashierCreationForm(BaseUserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CashierUpdateForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False)
    is_active = forms.BooleanField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'is_active')
        widgets = {
            'is_active': forms.CheckboxInput(),
        }

class BusinessDetailsForm(forms.ModelForm):
    """Form for shop admins to update their business details"""
    class Meta:
        model = UserProfile
        fields = ('shop_name', 'shop_address', 'shop_city', 'shop_phone', 'shop_email')
        widgets = {
            'shop_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your business name'
            }),
            'shop_address': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your business address'
            }),
            'shop_city': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your city'
            }),
            'shop_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your business phone'
            }),
            'shop_email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your business email'
            }),
        }
