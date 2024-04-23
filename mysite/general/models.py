# models.py

from django.contrib.auth.models import User
from django.db import models

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    two_factor_auth_enabled = models.BooleanField(default=False)
    language = models.CharField(max_length=10, choices=[('no', 'No'), ('en', 'English'), ('es', 'Spanish'), ('fr', 'French')], default='no')
    alias = models.CharField(max_length=50)
