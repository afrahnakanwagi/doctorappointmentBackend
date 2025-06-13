from rest_framework import serializers
from .models import DoctorAvailability, AppointmentSlot, Appointment
from users.serializers import UserSerializer

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    doctor = serializers.StringRelatedField(read_only=True)  # Optional: shows doctor name/email in response

    class Meta:
        model = DoctorAvailability
        fields = ['id', 'doctor', 'day_of_week', 'start_time', 'end_time', 'slot_duration', 'is_active']
        read_only_fields = ['id', 'doctor']


class AppointmentSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentSlot
        fields = ['id', 'date', 'start_time', 'end_time', 'is_booked']

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    appointment_date = serializers.SerializerMethodField()
    appointment_time = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_name', 'doctor_name', 'appointment_type',
            'status', 'appointment_date', 'appointment_time'
        ]

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()

    def get_doctor_name(self, obj):
        return obj.slot.doctor.get_full_name()

    def get_appointment_date(self, obj):
        return obj.slot.date

    def get_appointment_time(self, obj):
        return obj.slot.start_time

class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient = UserSerializer()
    slot = AppointmentSlotSerializer()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'slot', 'appointment_type',
            'status', 'reason', 'notes', 'created_at', 'updated_at'
        ] 
