from django.http import HttpResponse
from django.shortcuts import redirect, render
from accounts.models import User, UserProfile
from vendor.forms import VendorForm
from . forms import UserForm
from django.contrib import messages

# Create your views here.

def registerUser(request):
    if request.method == 'POST':
        print('The request: ',request.POST)
        form = UserForm(request.POST)
        if form.is_valid():
        #    Create the user using the form
        #    password = form.cleaned_data['password']
        #    user = form.save(commit=False)
        #    user.role = User.CUSTOMER
        #    user.set_password(password)
        #    user.save()

            # Create the user using create_user method
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(first_name = first_name, last_name = last_name, username = username, email = email, password = password)
            user.role = User.CUSTOMER
            user.save()
            messages.success(request, 'Your account has been registered successfully')
            return redirect('registerUser')
        else:
            print('Invalid form')
            print(form.errors)
    else:
        form = UserForm()
    context =  {
        'form': form
    }
    return render(request, 'accounts/registerUser.html', context)

def registerVendor(request):
    if request.method == 'POST':
        # store the data and create the user
        form = UserForm(request.POST)
        vendorForm = VendorForm(request.POST, request.FILES)
        if form.is_valid() and vendorForm.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(first_name = first_name, last_name = last_name, username = username, email = email, password = password)
            user.role = User.RESTAURANT
            user.save()
            vendor = vendorForm.save(commit=False)
            vendor.user = user
            user_profile = UserProfile.objects.get(user = user)
            print('USER PROFILE', user_profile)
            vendor.userProfile = user_profile
            vendor.save()
            messages.success(request, 'Your account has been registered successfully! Please wait for the approval.')
            return redirect('registerVendor')
        else: 
            print('Invalid form')
            print(form.errors)
    else: 
        form = UserForm()
        vendorForm = VendorForm()

    context = {
        'form': form,
        'vendorForm': vendorForm,
    }
    return render(request, 'accounts/registerVendor.html', context)