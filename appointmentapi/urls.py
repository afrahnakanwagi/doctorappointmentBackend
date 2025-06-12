from django.urls import path
from . import views

urlpatterns = [
    # Doctor Availability
    path('doctor/availability/', views.DoctorAvailabilityView.as_view(), name='doctor-availability'),
    path('doctor/availability/<int:pk>/', views.DoctorAvailabilityDetailView.as_view(), name='doctor-availability-detail'),
    
    # Appointment Slots
    path('slots/', views.AppointmentSlotView.as_view(), name='appointment-slots'),
    path('slots/<int:pk>/', views.AppointmentSlotDetailView.as_view(), name='appointment-slot-detail'),
    
    # Appointments
    path('appointments/', views.AppointmentView.as_view(), name='appointments'),
    path('appointments/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    path('appointments/<int:pk>/status/', views.AppointmentStatusView.as_view(), name='appointment-status'),
] 