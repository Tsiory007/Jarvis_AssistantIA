from django.shortcuts import render
from django.http import HttpResponse 

def Hello(request):
    return HttpResponse("Let's goo")

def AskJarvis(request):

    
    return HttpResponse("Ask Jarvis")