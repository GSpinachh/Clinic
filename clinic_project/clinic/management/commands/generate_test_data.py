from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
import random
from datetime import datetime, timedelta
from clinic.models import Specialty, Doctor, Patient, Appointment, Review

fake = Faker('ru_RU')

class Command(BaseCommand):
    help = 'Generate test data for clinic'
    
    def handle(self, *args, **options):
        self.stdout.write("Generating test data...")
        
        # Специальности
        specialties = ['Терапевт', 'Хирург', 'Кардиолог']
        for spec in specialties:
            Specialty.objects.get_or_create(
                name=spec,
                description=fake.text()
            )
        
        # Врачи 
        for _ in range(15):
            first_name = fake.first_name_male() if random.choice([True, False]) else fake.first_name_female()
            last_name = fake.last_name_male() if random.choice([True, False]) else fake.last_name_female()
            
            user = User.objects.create_user(
                username=fake.unique.user_name(),
                password='testpass123',
                first_name=first_name,
                last_name=last_name,
                email=fake.unique.email()
            )
            
            Doctor.objects.create(
                user=user,
                specialty=random.choice(Specialty.objects.all()),
                bio=fake.text(),
                education=", ".join(fake.words(5)),
                experience=random.randint(1, 30),
                photo='doctors/default.jpg'
            )
        
        # Пациенты 
        for _ in range(30):
            first_name = fake.first_name_male() if random.choice([True, False]) else fake.first_name_female()
            last_name = fake.last_name_male() if random.choice([True, False]) else fake.last_name_female()
            
            user = User.objects.create_user(
                username=fake.unique.user_name(),
                password='testpass123',
                first_name=first_name,
                last_name=last_name,
                email=fake.unique.email()
            )
            
            Patient.objects.create(
                user=user,
                phone=fake.phone_number(),
                birth_date=fake.date_of_birth(minimum_age=18, maximum_age=90),
                address=fake.address()
            )
        
        # Записи на прием 
        doctors = Doctor.objects.all()
        patients = Patient.objects.all()
        statuses = ['scheduled', 'completed', 'canceled']
        
        for _ in range(50):
            doctor = random.choice(doctors)
            patient = random.choice(patients)
            date = fake.date_between(start_date='-30d', end_date='+30d')
            time = fake.time_object()
            
            appointment = Appointment.objects.create(
                doctor=doctor,
                patient=patient,
                date=date,
                time=time,
                status=random.choice(statuses),
                notes=fake.text() if random.choice([True, False]) else '',
                diagnosis=fake.text() if appointment.status == 'completed' and random.choice([True, False]) else '',
                prescription=fake.text() if appointment.status == 'completed' and random.choice([True, False]) else ''
            )
            
            # Отзывы
            if appointment.status == 'completed' and random.choice([True, False]):
                Review.objects.create(
                    doctor=doctor,
                    patient=patient,
                    rating=random.randint(1, 5),
                    comment=fake.text(),
                    appointment=appointment
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully generated test data'))