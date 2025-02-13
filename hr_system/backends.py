from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get('login')
        
        try:
            # Attempt to get the user by email or username
            user = UserModel.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
            
            # Check the password
            if user.check_password(password):
                return user
                
        except UserModel.DoesNotExist:
            return None
        
        return None