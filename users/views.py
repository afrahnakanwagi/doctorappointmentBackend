from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import random
import string
from .models import User
from .serializers import (
    UserSerializer, UserListSerializer, LoginSerializer,
    OTPVerificationSerializer, RegisterSerializer,
    UserProfileSerializer, UserDetailSerializer, UserProfileEditSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.permissions import AllowAny
from .email_utils import send_otp_email

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def generate_otp(self):
        """Generate a 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))

    @swagger_auto_schema(
        operation_description="Register a new user",
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=UserSerializer
            ),
            400: "Bad Request"
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                otp = self.generate_otp()
                request.session[f'otp_{user.email}'] = otp
                
                # Try to send verification email
                email_sent = send_otp_email(user, otp)
                
                if email_sent:
                    return Response({
                        'message': 'User registered successfully. Please check your email for OTP verification.',
                        'user': serializer.data
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'message': 'User registered successfully but email verification failed. Please contact support.',
                        'user': serializer.data,
                        'error': 'Email sending failed. Please try again later or contact support.',
                        'debug_info': {
                            'template_id': settings.SENDGRID_TEMPLATE_ID,
                            'from_email': settings.DEFAULT_FROM_EMAIL
                        }
                    }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_description="Verify user's email using OTP",
        tags=['User Management'],
        request_body=OTPVerificationSerializer,
        responses={
            200: "Email verified successfully",
            400: "Invalid OTP"
        }
    )
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp_code']
            
            stored_otp = request.session.get(f'otp_{email}')
            if stored_otp and stored_otp == str(otp):
                user = User.objects.get(email=email)
                user.email_verified = True
                user.save()
                del request.session[f'otp_{email}']
                return Response({
                    'message': 'Email verified successfully'
                }, status=status.HTTP_200_OK)
            return Response({
                'message': 'Invalid OTP'
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_description="Login user with email and password",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=UserSerializer
            ),
            400: "Invalid credentials"
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            token = RefreshToken.for_user(user)

            dashboard_url = '/doctor-dashboard' if user.is_doctor else '/mom-dashboard'

            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(token),
                    'access': str(token.access_token),
                },
                'dashboard_url': dashboard_url,
                'role': 'doctor' if user.is_doctor else 'patient'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Logout user and blacklist refresh token",
        tags=['User Management'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            205: "Successfully logged out",
            400: "Bad Request"
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = (permissions.IsAdminUser,)

    @swagger_auto_schema(
        operation_description="List all users (Admin only)",
        tags=['User Management'],
        responses={
            200: UserListSerializer(many=True),
            403: "Permission denied"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Get user details",
        tags=['User Management'],
        responses={
            200: UserSerializer,
            404: "User not found"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        if self.request.user.is_staff:
            return super().get_object()
        return self.request.user

class UserActivationView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    @swagger_auto_schema(
        operation_description="Activate a user account (Admin only)",
        tags=['User Management'],
        responses={
            200: "User activated successfully",
            404: "User not found"
        }
    )
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            user.status = "Active"
            user.save()
            return Response({
                'message': 'User activated successfully'
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

class UserDeactivationView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    @swagger_auto_schema(
        operation_description="Deactivate a user account (Admin only)",
        tags=['User Management'],
        responses={
            200: "User deactivated successfully",
            404: "User not found"
        }
    )
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            user.status = "Inactive"
            user.save()
            return Response({
                'message': 'User deactivated successfully'
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

class UserProfileEditView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        operation_description="Update user profile",
        tags=['User Management'],
        request_body=UserSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request"
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Partially update user profile",
        tags=['User Management'],
        request_body=UserSerializer,
        responses={
            200: UserSerializer,
            400: "Bad Request"
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
