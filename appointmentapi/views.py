from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import DoctorAvailability, AppointmentSlot, Appointment
from .serializers import (
    DoctorAvailabilitySerializer,
    AppointmentSlotSerializer,
    AppointmentSerializer,
    AppointmentDetailSerializer
)

class DoctorAvailabilityView(generics.ListCreateAPIView):
    """
    API endpoint for managing doctor's availability
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DoctorAvailabilitySerializer

    def get_queryset(self):
        return DoctorAvailability.objects.filter(doctor=self.request.user)

    def perform_create(self, serializer):
        # Assign the logged-in user as the doctor
        serializer.save(doctor=self.request.user)

    @swagger_auto_schema(
        operation_description="Get doctor's availability schedule",
        tag="Appointment Schedules",
        responses={
            200: DoctorAvailabilitySerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create new availability schedule",
        tag="Appointment Schedules",
        request_body=DoctorAvailabilitySerializer,
        responses={
            201: DoctorAvailabilitySerializer,
            400: "Bad Request",
            401: "Unauthorized"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class DoctorAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for managing specific doctor availability
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DoctorAvailabilitySerializer

    def get_queryset(self):
        return DoctorAvailability.objects.filter(doctor=self.request.user)

class AppointmentSlotView(generics.ListCreateAPIView):
    """
    API endpoint for managing appointment slots
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSlotSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(doctor=self.request.user)

    @swagger_auto_schema(
        operation_description="Get available appointment slots",
        tag="Appointment Schedules",
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Filter slots by date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: AppointmentSlotSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        date = request.query_params.get('date')
        queryset = self.get_queryset()
        if date:
            queryset = queryset.filter(date=date)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AppointmentSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for managing specific appointment slot
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSlotSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(doctor=self.request.user)

class AppointmentView(generics.ListCreateAPIView):
    """
    API endpoint for managing appointments
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(slot__doctor=self.request.user)

    @swagger_auto_schema(
        operation_description="Get list of appointments",
        tag="Appointments Schedules",
        manual_parameters=[
            openapi.Parameter(
                'status',
                openapi.IN_QUERY,
                description="Filter by appointment status",
                type=openapi.TYPE_STRING,
                enum=['PENDING', 'CONFIRMED', 'REJECTED']
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Filter by appointment date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: AppointmentSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        status_filter = request.query_params.get('status')
        date_filter = request.query_params.get('date')
        
        queryset = self.get_queryset()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_filter:
            queryset = queryset.filter(slot__date=date_filter)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AppointmentDetailView(generics.RetrieveAPIView):
    """
    API endpoint for viewing appointment details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentDetailSerializer

    def get_queryset(self):
        return Appointment.objects.filter(slot__doctor=self.request.user)

    @swagger_auto_schema(
        operation_description="Get detailed information about an appointment",
        tag="Appointments Schedules",
        responses={
            200: AppointmentDetailSerializer,
            404: "Not Found",
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class AppointmentStatusView(generics.UpdateAPIView):
    """
    API endpoint for updating appointment status
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        return Appointment.objects.filter(slot__doctor=self.request.user)

    @swagger_auto_schema(
        operation_description="Update appointment status",
        tag="Appointments Schedules",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['PENDING', 'CONFIRMED', 'REJECTED']
                )
            }
        ),
        responses={
            200: AppointmentSerializer,
            400: "Bad Request",
            404: "Not Found",
            401: "Unauthorized"
        }
    )
    def patch(self, request, *args, **kwargs):
        appointment = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Appointment.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        appointment.status = new_status
        appointment.save()
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
