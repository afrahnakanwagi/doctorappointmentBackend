from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from users.models import User
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from .models import DoctorAvailability, AppointmentSlot, Appointment
from rest_framework.views import APIView

from .serializers import (
    DoctorAvailabilitySerializer,
    AppointmentSlotSerializer,
    AppointmentSerializer,
    AppointmentDetailSerializer,
    AppointmentCreateSerializer
)

def generate_slots_for_date(doctor, date):
    """Generate appointment slots for a specific date based on doctor's availability"""
    # Get the day of week for the date
    weekday = date.strftime('%a').upper()[:3]
    
    # Get doctor's availability for this day
    availabilities = DoctorAvailability.objects.filter(
        doctor=doctor,
        day_of_week=weekday,
        is_active=True
    )
    
    slots = []
    for availability in availabilities:
        current_time = availability.start_time
        while current_time < availability.end_time:
            # Check if slot already exists
            slot, created = AppointmentSlot.objects.get_or_create(
                doctor=doctor,
                date=date,
                start_time=current_time,
                defaults={
                    'end_time': (datetime.combine(date, current_time) + 
                               timedelta(minutes=availability.slot_duration)).time(),
                    'is_booked': False
                }
            )
            if created:
                slots.append(slot)
            
            # Move to next slot
            current_time = (datetime.combine(date, current_time) + 
                          timedelta(minutes=availability.slot_duration)).time()
    
    return slots

class GenerateSlotsCommand(BaseCommand):
    help = 'Generate appointment slots for a date range'

    def add_arguments(self, parser):
        parser.add_argument('doctor_id', type=int, help='Doctor ID')
        parser.add_argument('start_date', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('end_date', type=str, help='End date (YYYY-MM-DD)')

    def handle(self, *args, **options):
        try:
            doctor = User.objects.get(id=options['doctor_id'], is_doctor=True)
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
            
            current_date = start_date
            total_slots = 0
            
            while current_date <= end_date:
                slots = generate_slots_for_date(doctor, current_date)
                total_slots += len(slots)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Generated {len(slots)} slots for {current_date}'
                    )
                )
                current_date += timedelta(days=1)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully generated {total_slots} slots from {start_date} to {end_date}'
                )
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Doctor with ID {options["doctor_id"]} not found')
            )
        except ValueError as e:
            self.stdout.write(
                self.style.ERROR(f'Invalid date format: {str(e)}')
            )

class DoctorAvailabilityView(generics.ListCreateAPIView):
    """
    API endpoint for:
    - Doctors to view and create their availability.
    - Patients to view all doctor availability schedules.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DoctorAvailabilitySerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'is_patient') and user.is_patient:
            return DoctorAvailability.objects.all()
        elif hasattr(user, 'is_doctor') and user.is_doctor:
            return DoctorAvailability.objects.filter(doctor=user)
        else:
            return DoctorAvailability.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'is_doctor') and user.is_doctor:
            serializer.save(doctor=user)
        else:
            raise PermissionDenied("Only doctors can create availability schedules.")

    @swagger_auto_schema(
        operation_description="View availability schedules. Patients see all. Doctors see their own.",
        tags=["Appointment Schedules"],
        responses={
            200: DoctorAvailabilitySerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Create new availability schedule (Doctors only)",
        tags=["Appointment Schedules"],
        request_body=DoctorAvailabilitySerializer,
        responses={
            201: DoctorAvailabilitySerializer,
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class DoctorAvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for:
    - Doctors to view, update, and delete their own availability.
    - Patients to only view availability details.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DoctorAvailabilitySerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'is_doctor') and user.is_doctor:
            return DoctorAvailability.objects.filter(doctor=user)
        elif hasattr(user, 'is_patient') and user.is_patient:
            return DoctorAvailability.objects.all()  # Patients can retrieve all
        return DoctorAvailability.objects.none()

    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        if user.is_patient and self.request.method != "GET":
            raise PermissionDenied("Patients are not allowed to modify availability.")

        if user.is_doctor and obj.doctor != user:
            raise PermissionDenied("You can only access your own availability.")

        return obj

class AppointmentSlotView(generics.ListCreateAPIView):
    """
    API endpoint for managing appointment slots
    - Doctors can create and manage their slots
    - Patients can view available slots
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSlotSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            return AppointmentSlot.objects.filter(doctor=user)
        else:
            # For patients, show all available slots
            return AppointmentSlot.objects.filter(is_booked=False)

    @swagger_auto_schema(
        operation_description="Get available appointment slots",
        tag="Appointment Schedules",
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Filter slots by date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'doctor_id',
                openapi.IN_QUERY,
                description="Filter slots by doctor ID",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'generate_slots',
                openapi.IN_QUERY,
                description="Generate slots for the specified date (true/false)",
                type=openapi.TYPE_BOOLEAN
            )
        ],
        responses={
            200: AppointmentSlotSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request, *args, **kwargs):
        date_str = request.query_params.get('date')
        doctor_id = request.query_params.get('doctor_id')
        generate_slots = request.query_params.get('generate_slots', 'false').lower() == 'true'
        
        queryset = self.get_queryset()
        
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(date=date)
                
                # Generate slots if requested
                if generate_slots and request.user.is_doctor:
                    generate_slots_for_date(request.user, date)
                    queryset = self.get_queryset().filter(date=date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """Create slots for a date range"""
        if not request.user.is_doctor:
            raise PermissionDenied("Only doctors can create slots")
            
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {"error": "Both start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        current_date = start_date
        slots_created = []
        
        while current_date <= end_date:
            slots = generate_slots_for_date(request.user, current_date)
            slots_created.extend(slots)
            current_date += timedelta(days=1)
            
        serializer = self.get_serializer(slots_created, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AppointmentSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for managing specific appointment slot
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSlotSerializer

    def get_queryset(self):
        return AppointmentSlot.objects.filter(doctor=self.request.user)


class AppointmentView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            return Appointment.objects.filter(slot__doctor=user)
        elif user.is_patient:
            return Appointment.objects.filter(patient=user)
        return Appointment.objects.none()

    @swagger_auto_schema(
        operation_description="Get list of appointments",
        tags=["Appointments Schedules"],
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
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        appointment_data = serializer.validated_data
        patient = appointment_data.get('patient_obj')
        doctor = appointment_data.get('doctor_obj')
        appointment_date = appointment_data.get('appointment_date')
        appointment_start_time = appointment_data.get('appointment_start_time')

        try:
            availability = DoctorAvailability.objects.filter(
                doctor=doctor,
                day_of_week=appointment_date.strftime('%a').upper()[:3],
                is_active=True
            ).first()

            if not availability:
                raise ValidationError({'appointment_date': 'Doctor is not available on this day.'})

            start_datetime = datetime.combine(appointment_date, appointment_start_time)
            end_datetime = start_datetime + timedelta(minutes=availability.slot_duration)
            end_time = end_datetime.time()

            slot, created = AppointmentSlot.objects.get_or_create(
                doctor=doctor,
                date=appointment_date,
                start_time=appointment_start_time,
                defaults={
                    'end_time': end_time,
                    'is_booked': True
                }
            )

            if not created and slot.is_booked:
                raise ValidationError({'appointment_start_time': 'This time slot is already booked.'})

            appointment = Appointment.objects.create(
                patient=patient,
                slot=slot,
                appointment_type=appointment_data.get('appointment_type'),
                reason=appointment_data.get('reason', ''),
                notes=appointment_data.get('notes', ''),
                status='PENDING'
            )

            return appointment

        except IntegrityError as e:
            raise ValidationError({'error': f'Database error: {str(e)}'})
        except Exception as e:
            raise ValidationError({'error': f'Unexpected error: {str(e)}'})

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            appointment = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({
                'message': 'Appointment successfully created and is pending confirmation.',
                'appointment': AppointmentSerializer(appointment).data,
                'status': 'PENDING'
            }, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            return Response({'error': str(e.detail)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    

class AppointmentDetailView(generics.RetrieveAPIView):
    """
    API endpoint for viewing appointment details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            return Appointment.objects.filter(slot__doctor=user)
        elif user.is_patient:
            return Appointment.objects.filter(patient=user)
        return Appointment.objects.none()

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
    API endpoint for doctors to update appointment status
    (PENDING → CONFIRMED/REJECTED)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        if self.request.user.is_doctor:
            return Appointment.objects.filter(slot__doctor=self.request.user)
        return Appointment.objects.none()

    @swagger_auto_schema(
        operation_description="Update appointment status. Only doctors can update status of their appointments.",
        tag="Appointments Schedules",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['status'],
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['CONFIRMED', 'REJECTED'], 
                    description="New status for the appointment (CONFIRMED or REJECTED)"
                )
            }
        ),
        responses={
            200: AppointmentSerializer,
            400: "Bad Request - Invalid status or invalid transition",
            403: "Forbidden - User is not the doctor for this appointment",
            404: "Not Found",
            401: "Unauthorized"
        }
    )
    def patch(self, request, *args, **kwargs):
        if not request.user.is_doctor:
            return Response(
                {"error": "Only doctors can update appointment status"},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = ['CONFIRMED', 'REJECTED']
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Only {valid_statuses} are allowed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if appointment.status != 'PENDING':
            return Response(
                {"error": f"Can only update status from PENDING. Current status is {appointment.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = new_status
        appointment.save()

        self._send_status_notification(appointment, new_status)

        serializer = self.get_serializer(appointment)
        return Response(serializer.data)

    def _send_status_notification(self, appointment, new_status):
        pass
@api_view(['GET'])
def appointment_type_choices(request):
    choices = [{'value': c[0], 'label': c[1]} for c in Appointment.TYPE_CHOICES]
    return Response(choices)


class AvailableSlotsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get available appointment slots",
        tags=["Appointments Schedules"],
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Filter by date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'doctor_id',
                openapi.IN_QUERY,
                description="Filter by doctor ID",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: AppointmentSlotSerializer(many=True),
            401: "Unauthorized"
        }
    )
    def get(self, request):
        date_str = request.query_params.get('date')
        doctor_id = request.query_params.get('doctor_id')

        try:
            slots = []
            if date_str:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date = datetime.now().date()

            availabilities = DoctorAvailability.objects.filter(
                day_of_week=date.strftime('%a').upper()[:3],
                is_active=True
            )

            if doctor_id:
                availabilities = availabilities.filter(doctor_id=doctor_id)

            for availability in availabilities:
                start_time = datetime.combine(date, availability.start_time)
                end_time = datetime.combine(date, availability.end_time)
                current_time = start_time

                while current_time < end_time:
                    slot_time = current_time.time()
                    if not AppointmentSlot.objects.filter(
                        doctor=availability.doctor,
                        date=date,
                        start_time=slot_time,
                        is_booked=True
                    ).exists():
                        slots.append({
                            'doctor': {
                                'id': availability.doctor.id,
                                'username': availability.doctor.username
                            },
                            'date': date,
                            'start_time': slot_time,
                            'end_time': (current_time + timedelta(minutes=availability.slot_duration)).time(),
                            'is_booked': False
                        })
                    current_time += timedelta(minutes=availability.slot_duration)

            serializer = AppointmentSlotSerializer(slots, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response({'error': 'Invalid date format.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)