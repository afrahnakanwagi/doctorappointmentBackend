from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.validators import RegexValidator
from datetime import datetime
from django.utils import timezone

class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    
    is_patient = models.BooleanField(default=True)
    is_doctor = models.BooleanField(default=False)
    
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    address = models.TextField(blank=True)
    
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Disabled", "Disabled"),
        ("Pending", "Pending")
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    
    specialization = models.CharField(max_length=100, blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    available_days = models.CharField(max_length=100, blank=True) 
    available_hours = models.CharField(max_length=100, blank=True)
    
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True, default=None)
    
    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-created_at']

    def __str__(self):
        role = "Patient" if self.is_patient else "Doctor" if self.is_doctor else "User"
        return f"{self.username} ({role}) - {self.email}"

    def get_tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def get_role_display(self):
        if self.is_doctor:
            return "Doctor"
        elif self.is_patient:
            return "Patient"
        return "User"

    def save(self, *args, **kwargs):
        if self.is_doctor:
            self.is_patient = False
        elif self.is_patient:
            self.is_doctor = False
        
        if self.email_verified and self.status == "Pending":
            self.status = "Active"
            
        super().save(*args, **kwargs)
