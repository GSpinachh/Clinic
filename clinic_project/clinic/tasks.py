from django.utils import timezone
from .models import Appointment
from django.core.mail import send_mail
from django.conf import settings

# напоминание
def send_appointment_reminders():
    tomorrow = timezone.now() + timezone.timedelta(days=1)
    appointments = Appointment.objects.filter(
        date=tomorrow.date(),
        status='scheduled'
    ).select_related('patient__user', 'doctor__user')
    
    for appointment in appointments:
        send_mail(
            subject=f"Напоминание о приеме у {appointment.doctor.user.get_full_name()}",
            message=f"У вас запланирован прием на {appointment.date} в {appointment.time}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.patient.user.email],
            fail_silently=True,
        )