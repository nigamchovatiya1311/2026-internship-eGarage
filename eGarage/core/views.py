from django.shortcuts import render,redirect,HttpResponse
from django.contrib.auth import authenticate,login
from .forms import UserSignUpForm, UserLoginForm

# Create your views here.
def userSignupView(request):
    if request.method =="POST":
      form = UserSignUpForm(request.POST or None)
      if form.is_valid():
        form.save()
        return redirect('login') 
      else:
        return render(request,'core/signup.html',{'form':form})  
    else:
        form = UserSignUpForm()
        return render(request,'core/signup.html',{'form':form})
    



def userLoginView(request):
  if request.method == "POST":
      form = UserLoginForm(request.POST or None)

      if form.is_valid():
        print(form.cleaned_data)
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request,email=email,password=password) #it will check in database..

        #user redirect in dashboard according role
        if user:
           login(request, user)
           if user.role == 'admin':
              return redirect('admin_dashboard') 
           elif user.role == 'customer':
              return redirect('customer_dashboard')
           elif user.role == 'service_provider':
              return redirect('serviceProvider_dashboard')
        else:
          return render(request,'core/login.html',{'form':form}) 

  else:
      form = UserLoginForm()
      return render(request,'core/login.html',{'form':form})     