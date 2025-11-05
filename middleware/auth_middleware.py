from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Cache reversed URLs at initialization to avoid repeated URL resolution
        self.exempt_urls = [
            reverse('login'),
            reverse('register'),
            reverse('password_reset'),
            '/static/',  # Allow static files
            '/media/',   # Allow media files
        ]

    def __call__(self, request):
        # Check if the user is not authenticated and not accessing an exempt URL
        if not request.user.is_authenticated:
            current_path = request.path_info
            if not any(current_path.startswith(url) for url in self.exempt_urls):
                return redirect('login')

        response = self.get_response(request)
        return response 