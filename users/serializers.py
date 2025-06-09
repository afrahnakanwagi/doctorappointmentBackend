from rest_framework import serializers
from django.contrib.auth import authenticate
from users.models import User
from vendors.serializers import VendorSerializer  # optional, if needed

# ---------------------- USER SERIALIZER ----------------------

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone_number", "is_patient", 
            "is_doctor", "email_verified", "status", "role"
        ]

    def get_role(self, obj):
        if obj.is_doctor:
            return "Doctor"
        elif obj.is_patient:
            return "Patient"
        else:
            return "User"

# ---------------------- USER LIST SERIALIZER ----------------------

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users with basic info"""
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "status", "is_active", "date_joined"]

    def get_role(self, obj):
        if obj.is_doctor:
            return "Doctor"
        elif obj.is_patient:
            return "Patient"
        else:
            return "User"

# ---------------------- OTP VERIFICATION SERIALIZER ----------------------

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.IntegerField(required=True)

# ---------------------- LOGIN SERIALIZER ----------------------

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.email_verified:
            raise serializers.ValidationError("Please verify your email before logging in.")
        data["user"] = user
        return data
