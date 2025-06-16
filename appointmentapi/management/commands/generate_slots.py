from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from users.models import User
from appointmentapi.models import DoctorAvailability, AppointmentSlot

class Command(BaseCommand):
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
                # Get the day of week for the date
                weekday = current_date.strftime('%a').upper()[:3]
                
                # Get doctor's availability for this day
                availabilities = DoctorAvailability.objects.filter(
                    doctor=doctor,
                    day_of_week=weekday,
                    is_active=True
                )
                
                for availability in availabilities:
                    current_time = availability.start_time
                    while current_time < availability.end_time:
                        # Check if slot already exists
                        slot, created = AppointmentSlot.objects.get_or_create(
                            doctor=doctor,
                            date=current_date,
                            start_time=current_time,
                            defaults={
                                'end_time': (datetime.combine(current_date, current_time) + 
                                           timedelta(minutes=availability.slot_duration)).time(),
                                'is_booked': False
                            }
                        )
                        if created:
                            total_slots += 1
                        
                        # Move to next slot
                        current_time = (datetime.combine(current_date, current_time) + 
                                      timedelta(minutes=availability.slot_duration)).time()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processed slots for {current_date}'
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