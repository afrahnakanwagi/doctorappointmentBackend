from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from rest_framework_simplejwt.tokens import RefreshToken

class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, default='')

    is_patient = models.BooleanField(default=True)
    is_doctor = models.BooleanField(default=False)

    email_verified = models.BooleanField(default=False)
    STATUS_CHOICES = [("Active", "Active"), ("Inactive", "Inactive"), ("Disabled", "Disabled")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")

    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        role = "Patient" if self.is_patient else "Doctor" if self.is_doctor else "User"
        return f"{self.username} ({role}) - {self.email}"

    def get_tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
