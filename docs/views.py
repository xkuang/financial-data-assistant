from django.shortcuts import render

def documentation(request):
    """Render the documentation page"""
    return render(request, 'documentation.html') 