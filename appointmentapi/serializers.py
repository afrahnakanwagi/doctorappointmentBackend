from rest_framework import serializers
from .models import DoctorAvailability, AppointmentSlot, Appointment
from users.serializers import UserSerializer
from users.models import User

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    doctor = serializers.StringRelatedField(read_only=True)  # Optional: shows doctor name/email in response

    class Meta:
        model = DoctorAvailability
        fields = ['id', 'doctor', 'day_of_week', 'start_time', 'end_time', 'slot_duration', 'is_active']
        read_only_fields = ['id', 'doctor']

class AppointmentSlotSerializer(serializers.ModelSerializer):
    doctor = UserSerializer(read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = [
            'id',
            'doctor',     
            'date',
            'start_time',
            'end_time',
            'duration_minutes',  
            'is_booked',
            'is_available',    
            'created_at',
        ]

    def get_duration_minutes(self, obj):
  
        start = obj.start_time
        end = obj.end_time

        duration = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
        return duration

    def get_is_available(self, obj):
    
        from django.utils import timezone
        now = timezone.now()
        slot_datetime = timezone.datetime.combine(obj.date, obj.start_time)
        slot_datetime = timezone.make_aware(slot_datetime, timezone.get_current_timezone())

        return not obj.is_booked and slot_datetime > now


class AppointmentCreateSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(write_only=True, required=False)
    patient = serializers.CharField(write_only=True, required=True)
    appointment_date = serializers.DateField(write_only=True)
    appointment_start_time = serializers.TimeField(write_only=True)

    class Meta:
        model = Appointment
        fields = [
            'patient',
            'doctor_id',
            'appointment_date',
            'appointment_start_time',
            'appointment_type',
            'reason',
            'notes',
        ]
        read_only_fields = ['status']

    def validate(self, data):
        patient = data.get('patient')
        appointment_date = data.get('appointment_date')
        appointment_start_time = data.get('appointment_start_time')
        doctor_id = data.get('doctor_id')

        try:
            patient_obj = User.objects.get(username=patient, role='patient')
        except User.DoesNotExist:
            try:
                patient_obj = User.objects.get(email=patient, role='patient')
            except User.DoesNotExist:
                raise serializers.ValidationError({'patient': 'Patient not found.'})

        if patient_obj != self.context['request'].user:
            raise serializers.ValidationError({'patient': 'You can only book appointments for yourself.'})

        data['patient_obj'] = patient_obj

        availability_qs = DoctorAvailability.objects.filter(
            day_of_week=appointment_date.strftime('%a').upper()[:3],
            start_time__lte=appointment_start_time,
            end_time__gte=appointment_start_time,
            is_active=True
        )

        if doctor_id:
            availability_qs = availability_qs.filter(doctor_id=doctor_id)
            try:
                doctor = User.objects.get(id=doctor_id, is_doctor=True)
            except User.DoesNotExist:
                raise serializers.ValidationError({'doctor_id': 'Doctor not found.'})
        else:
            availability_qs = availability_qs.select_related('doctor')

        availability = availability_qs.first()
        if not availability:
            raise serializers.ValidationError({
                'appointment_date': 'No doctor is available for this date and time.'
            })

        doctor = availability.doctor
        data['doctor_obj'] = doctor
        data['doctor_id'] = doctor.id

        existing_slot = AppointmentSlot.objects.filter(
            doctor=doctor,
            date=appointment_date,
            start_time=appointment_start_time,
            is_booked=True
        ).first()

        if existing_slot:
            raise serializers.ValidationError({'appointment_start_time': 'This time slot is already booked.'})

        return data

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'gender', 'date_of_birth']

class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    slot = serializers.StringRelatedField() 

    class Meta:
        model = Appointment
        fields = '__all__'

class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient = UserSerializer()
    slot = AppointmentSlotSerializer()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'slot', 'appointment_type',
            'status', 'reason', 'notes', 'created_at', 'updated_at'
        ] 
