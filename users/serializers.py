from rest_framework import serializers
from django.contrib.auth import authenticate
from users.models import User
from drf_yasg.utils import swagger_serializer_method
from django.utils import timezone
from datetime import datetime

# ---------------------- REGISTRATION SERIALIZER ----------------------

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=['patient', 'doctor'], write_only=True)
    
    # Common fields
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    address = serializers.CharField(required=False)
    
    # Doctor specific fields
    specialization = serializers.CharField(required=False)
    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    available_days = serializers.CharField(required=False)
    available_hours = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "password", "phone_number",
            "role", "is_patient", "is_doctor",
            # Common fields
            "date_of_birth", "gender", "address",
            # Doctor fields
            "specialization", "consultation_fee", "available_days", "available_hours"
        ]
        extra_kwargs = {
            'is_patient': {'read_only': True},
            'is_doctor': {'read_only': True}
        }

    def validate(self, data):
        role = data.pop('role', None)
        
        # Validate role-specific fields
        if role == 'doctor':
            required_fields = ['specialization']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"{field} is required for doctor registration")
            data['is_doctor'] = True
            data['is_patient'] = False
        else:  # patient
            data['is_patient'] = True
            data['is_doctor'] = False
        
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

# ---------------------- USER SERIALIZER ----------------------

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone_number", "is_patient", 
            "is_doctor", "email_verified", "status", "role", "full_name",
            # Common fields
            "date_of_birth", "gender", "address",
            # Doctor fields
            "specialization", "consultation_fee", "available_days", "available_hours",
            # System fields
            "created_at", "updated_at", "last_login"
        ]
        read_only_fields = ['email_verified', 'status', 'created_at', 'updated_at', 'last_login']

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_role(self, obj):
        return obj.get_role_display()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_full_name(self, obj):
        return obj.get_full_name()

# ---------------------- USER LIST SERIALIZER ----------------------

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users with basic info"""
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "role", "status", 
            "is_active", "date_joined", "full_name",
            "specialization" if User.is_doctor else None
        ]

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_role(self, obj):
        return obj.get_role_display()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_full_name(self, obj):
        return obj.get_full_name()

# ---------------------- OTP VERIFICATION SERIALIZER ----------------------

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.IntegerField(required=True)

# ---------------------- LOGIN SERIALIZER ----------------------

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=['patient', 'doctor'])

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        
        # Check if the selected role matches the user's role
        if data["role"] == "doctor" and not user.is_doctor:
            raise serializers.ValidationError("This account is not registered as a doctor.")
        elif data["role"] == "patient" and not user.is_patient:
            raise serializers.ValidationError("This account is not registered as a patient.")
        
        data["user"] = user
        return data

# ---------------------- USER PROFILE SERIALIZER ----------------------

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for detailed user profile information"""
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone_number", "is_patient", 
            "is_doctor", "email_verified", "status", "role", "full_name", "age",
            # Common fields
            "date_of_birth", "gender", "address",
            # Doctor fields
            "specialization", "consultation_fee", "available_days", "available_hours",
            # System fields
            "created_at", "updated_at", "last_login"
        ]
        read_only_fields = [
            'email', 'username', 'email_verified', 'status', 
            'created_at', 'updated_at', 'last_login', 'is_patient', 'is_doctor'
        ]

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_role(self, obj):
        return obj.get_role_display()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_full_name(self, obj):
        return obj.get_full_name()

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField())
    def get_age(self, obj):
        if obj.date_of_birth:
            today = timezone.now().date()
            return today.year - obj.date_of_birth.year - (
                (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        return None

    def validate_phone_number(self, value):
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits long")
        return value

    def validate_consultation_fee(self, value):
        if self.instance and self.instance.is_doctor and value is not None:
            if value < 0:
                raise serializers.ValidationError("Consultation fee cannot be negative")
        return value

    def validate_available_days(self, value):
        if self.instance and self.instance.is_doctor and value:
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            days = [day.strip() for day in value.split(',')]
            invalid_days = [day for day in days if day not in valid_days]
            if invalid_days:
                raise serializers.ValidationError(f"Invalid days: {', '.join(invalid_days)}")
        return value

    def validate_available_hours(self, value):
        if self.instance and self.instance.is_doctor and value:
            try:
                start, end = value.split('-')
                start_time = datetime.strptime(start.strip(), '%H:%M').time()
                end_time = datetime.strptime(end.strip(), '%H:%M').time()
                if end_time <= start_time:
                    raise serializers.ValidationError("End time must be after start time")
            except ValueError:
                raise serializers.ValidationError("Time format must be HH:MM-HH:MM (e.g., 09:00-17:00)")
        return value

class UserDetailSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    appointments_count = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone_number", "is_patient", 
            "is_doctor", "email_verified", "status", "role", "full_name", "age",
            "date_of_birth", "gender", "address",
            "specialization", "consultation_fee", "available_days", "available_hours",
            "appointments_count", "rating",
            "created_at", "updated_at", "last_login"
        ]
        read_only_fields = [
            'email', 'username', 'email_verified', 'status', 
            'created_at', 'updated_at', 'last_login', 'is_patient', 'is_doctor',
            'appointments_count', 'rating'
        ]

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_role(self, obj):
        return obj.get_role_display()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_full_name(self, obj):
        return obj.get_full_name()

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField())
    def get_age(self, obj):
        if obj.date_of_birth:
            today = timezone.now().date()
            return today.year - obj.date_of_birth.year - (
                (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        return None

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField())
    def get_appointments_count(self, obj):
        if obj.is_doctor:
            return obj.doctor_appointments.count()
        return obj.patient_appointments.count()

    @swagger_serializer_method(serializer_or_field=serializers.FloatField())
    def get_rating(self, obj):
        if obj.is_doctor:
            ratings = obj.doctor_ratings.all()
            if ratings:
                return sum(r.rating for r in ratings) / len(ratings)
        return None

class UserProfileEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "phone_number", "address",
            "specialization", "consultation_fee", 
            "available_days", "available_hours"
        ]

    def validate_phone_number(self, value):
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits long")
        return value

    def validate_consultation_fee(self, value):
        if self.instance and self.instance.is_doctor and value is not None:
            if value < 0:
                raise serializers.ValidationError("Consultation fee cannot be negative")
        return value

    def validate_available_days(self, value):
        if self.instance and self.instance.is_doctor and value:
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            days = [day.strip() for day in value.split(',')]
            invalid_days = [day for day in days if day not in valid_days]
            if invalid_days:
                raise serializers.ValidationError(f"Invalid days: {', '.join(invalid_days)}")
        return value

    def validate_available_hours(self, value):
        if self.instance and self.instance.is_doctor and value:
            try:
                start, end = value.split('-')
                start_time = datetime.strptime(start.strip(), '%H:%M').time()
                end_time = datetime.strptime(end.strip(), '%H:%M').time()
                if end_time <= start_time:
                    raise serializers.ValidationError("End time must be after start time")
            except ValueError:
                raise serializers.ValidationError("Time format must be HH:MM-HH:MM (e.g., 09:00-17:00)")
        return value

class UserPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return data

class UserEmailChangeSerializer(serializers.Serializer):
    new_email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate_new_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered")
        return value

class UserDeactivationSerializer(serializers.Serializer):
    password = serializers.CharField(required=True)
    reason = serializers.CharField(required=False)

class UserActivationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True)

class UserSearchSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone_number",
            "role", "full_name", "rating",
            "specialization", "consultation_fee",
            "available_days", "available_hours"
        ]

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_role(self, obj):
        return obj.get_role_display()

    @swagger_serializer_method(serializer_or_field=serializers.CharField())
    def get_full_name(self, obj):
        return obj.get_full_name()

    @swagger_serializer_method(serializer_or_field=serializers.FloatField())
    def get_rating(self, obj):
        if obj.is_doctor:
            ratings = obj.doctor_ratings.all()
            if ratings:
                return sum(r.rating for r in ratings) / len(ratings)
        return None


