import os
from datetime import datetime, date, timedelta
import random
from io import BytesIO
from django.conf import settings
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Q
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

def generate_pdf(appointment):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    styles = getSampleStyleSheet()
    elements = []
    
    title = Paragraph("Медицинская справка", styles['Title'])
    elements.append(title)
    
    clinic_info = [
        ["Клиника:", "Частная клиника 'Здоровье'"],
        ["Адрес:", "г. Ульяновкс, ул. Медицинская, 42"],
        ["Лицензия:", "ЛО-77-01-012345 от 12.03.2020"]
    ]
    clinic_table = Table(clinic_info, colWidths=[100, 300])
    elements.append(clinic_table)
    
    patient = appointment.patient
    patient_data = [
        ["Пациент:", f"{patient.last_name} {patient.first_name} {patient.middle_name}"],
        ["Дата рождения:", patient.birth_date.strftime("%d.%m.%Y")],
        ["Номер карты:", f"№{patient.id:08d}"]
    ]
    patient_table = Table(patient_data, colWidths=[100, 300])
    elements.append(patient_table)
    
    appointment_data = [
        ["Дата приема:", appointment.date.strftime("%d.%m.%Y")],
        ["Время:", appointment.time.strftime("%H:%M")],
        ["Врач:", f"{appointment.doctor.specialization.name} {appointment.doctor.last_name} {appointment.doctor.first_name[0]}.{appointment.doctor.middle_name[0]}."],
        ["Диагноз:", appointment.diagnosis or "Не указан"],
        ["Рекомендации:", appointment.recommendations or "Не указаны"]
    ]
    app_table = Table(appointment_data, colWidths=[100, 300])
    elements.append(app_table)

    signature = Paragraph(f"Дата выдачи: {date.today().strftime('%d.%m.%Y')}<br/><br/>Подпись врача: _________________", styles['Normal'])
    elements.append(signature)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_appointment_confirmation(appointment):
    subject = f"Подтверждение записи на {appointment.date.strftime('%d.%m.%Y')}"
    message = render_to_string('clinic/appointment_email.html', {
        'appointment': appointment,
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.user.email],
        fail_silently=False,
    )

def get_available_time_slots(doctor, date):
    from .models import Appointment
    
    start_time = datetime.strptime('09:00', '%H:%M').time()
    end_time = datetime.strptime('18:00', '%H:%M').time()
    
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date=date
    ).values_list('time', flat=True)
    
    time_slots = []
    current_time = start_time
    
    while current_time < end_time:
        if current_time not in appointments:
            time_slots.append(current_time.strftime('%H:%M'))
        current_time = (datetime.combine(date.today(), current_time) + timedelta(minutes=30)).time()
    
    return time_slots

def generate_test_patients(count=30):
    from django.contrib.auth.models import User
    from .models import Patient
    
    first_names = ['Иван', 'Алексей', 'Мария', 'Ольга', 'Сергей']
    last_names = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов']
    
    for i in range(count):
        username = f'patient_{i}'
        email = f'{username}@example.com'
        password = 'test123'
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        Patient.objects.create(
            user=user,
            first_name=random.choice(first_names),
            last_name=random.choice(last_names),
            middle_name=random.choice(['Иванович', 'Алексеевич', 'Олегович', '']),
            birth_date=date.today() - timedelta(days=random.randint(18*365, 70*365)),
            gender=random.choice(['M', 'F']),
            phone=f'+7{random.randint(9000000000, 9999999999)}'
        )

def calculate_doctor_rating(doctor):
    from .models import Review
    reviews = Review.objects.filter(doctor=doctor)
    if reviews.exists():
        return round(sum([review.rating for review in reviews]) / reviews.count(), 1)
    return 0.0

def validate_appointment_date(date_obj):

    if date_obj < date.today():
        return False, "Нельзя записаться на прошедшую дату"
    if date_obj.weekday() >= 5:  
        return False, "Клиника не работает в выходные" # 5 и 6
    return True, ""