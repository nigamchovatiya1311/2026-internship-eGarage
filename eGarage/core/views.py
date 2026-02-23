from django.shortcuts import render,redirect
from .forms import UserSignUpForm

# Create your views here.
def userSignupView(request):
    if request.method =="POST":
      form = UserSignUpForm(request.POST or None)
      if form.is_valid():
        form.save()
        return redirect('login') #error
      else:
        return render(request,'core/signup.html',{'form':form})  
    else:
        form = UserSignUpForm()
        return render(request,'core/signup.html',{'form':form})