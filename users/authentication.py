from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class UserProfileBackend(ModelBackend):
    """
    Custom authentication backend that checks both User.is_active and UserProfile.is_active
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None
        
        # Check password
        if user.check_password(password):
            try:
                # Check if user profile exists and is active
                user_profile = user.profile
                if not user_profile.is_active:
                    return None
            except UserProfile.DoesNotExist:
                # If no profile exists, create one (for backward compatibility)
                UserProfile.objects.create(user=user)
            
            return user
        return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            try:
                # Check if user profile is active
                user_profile = user.profile
                if not user_profile.is_active:
                    return None
            except UserProfile.DoesNotExist:
                return None
            
            return user
        except User.DoesNotExist:
            return None
