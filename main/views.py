from django.shortcuts import render

# Create your views here.
def home_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')


        return render(request, 'index.html')