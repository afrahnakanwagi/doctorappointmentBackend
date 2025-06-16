from django.db import models
from django.utils import timezone
from users.models import User

class DoctorAvailability(models.Model):
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]
    
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30)  # in minutes
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Doctor Availabilities"
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.get_full_name()} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

class AppointmentSlot(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ('doctor', 'date', 'start_time')
    
    def __str__(self):
        return f"Slot on {self.date} at {self.start_time} with Dr. {self.doctor.get_full_name()}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('REJECTED', 'Rejected'),
    ]
    
    TYPE_CHOICES = [
        ('PRENATAL', 'Prenatal Checkup'),
        ('POSTNATAL', 'Postnatal Checkup'),
        ('GENERAL', 'General Consultation'),
        ('ROUTINE', 'Routine Checkup'),
        ('SPECIALIST', 'Specialist Consultation'),
        ('EMERGENCY', 'Emergency Visit'),
        ('FOLLOW_UP', 'Follow-up Visit'),
        ('LAB_TEST', 'Lab Test'),
        ('DIAGNOSTIC', 'Diagnostic'),
        ('VACCINATION', 'Vaccination'),
        ('OTHER', 'Other'),
    ]
    
    slot = models.OneToOneField(AppointmentSlot, on_delete=models.CASCADE, related_name='appointment', null=True, blank=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_appointments')
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-slot__date', '-slot__start_time']
    
    def __str__(self):
        return f"{self.patient.get_full_name()} with Dr. {self.slot.doctor.get_full_name()} on {self.slot.date} at {self.slot.start_time}"