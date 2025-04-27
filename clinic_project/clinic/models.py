import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count
from datetime import timedelta

def doctor_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"doctor_{instance.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return os.path.join('doctors', filename)

def patient_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"patient_{instance.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return os.path.join('patients', filename)

def document_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"doc_{instance.patient.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return os.path.join('medical_documents', filename)

class Specialty(models.Model):
    name = models.CharField(_('Название'), max_length=100, unique=True)
    slug = models.SlugField(_('URL-адрес'), max_length=100, unique=True)
    description = models.TextField(_('Описание'), blank=True)
    icon = models.CharField(_('Иконка'), max_length=50, blank=True, 
                          help_text=_('Название иконки из Font Awesome'))

    class Meta:
        app_label = 'clinic'
        verbose_name = _('Специальность')
        verbose_name_plural = _('Специальности')
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('doctor_list_by_specialty', kwargs={'specialty_slug': self.slug})

    @property
    def doctor_count(self):
        return self.doctor_set.filter(is_active=True).count()

    @property
    def average_rating(self):
        return self.doctor_set.filter(is_active=True).aggregate(
            avg_rating=Avg('review__rating')
        )['avg_rating']

class Doctor(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,
        verbose_name=_('Специальность')
    )
    photo = models.ImageField(
        _('Фотография'),
        upload_to=doctor_photo_path,
        default='doctors/default.jpg'
    )
    bio = models.TextField(_('О себе'), blank=True)
    education = models.TextField(_('Образование'))
    experience = models.PositiveIntegerField(
        _('Опыт работы (лет)'),
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    is_active = models.BooleanField(_('Активен'), default=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Врач')
        verbose_name_plural = _('Врачи')
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.specialty})"

    def get_absolute_url(self):
        return reverse('doctor_detail', kwargs={'pk': self.pk})

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def average_rating(self):
        return self.review_set.aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0

    @property
    def review_count(self):
        return self.review_set.count()

    def get_available_slots(self, date):
        booked_slots = self.appointment_set.filter(
            date=date,
            status='scheduled'
        ).values_list('time', flat=True)

        all_slots = [
            (time.hour, time.minute) 
            for time in [
                timezone.datetime(2000, 1, 1, h, m) 
                for h in range(9, 18) 
                for m in [0, 30] 
            ]
        ]

        available_slots = [
            timezone.datetime(2000, 1, 1, h, m).time()
            for h, m in all_slots
            if timezone.datetime(2000, 1, 1, h, m).time() not in booked_slots
        ]

        return available_slots

class Patient(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    phone = models.CharField(
        _('Телефон'),
        max_length=20,
        help_text=_('Формат: +7 (XXX) XXX-XX-XX')
    )
    birth_date = models.DateField(_('Дата рождения'))
    address = models.TextField(_('Адрес'))
    photo = models.ImageField(
        _('Фотография'),
        upload_to=patient_photo_path,
        blank=True,
        null=True
    )
    medical_history = models.TextField(
        _('Медицинская история'),
        blank=True,
        help_text=_('Хронические заболевания, аллергии и т.д.')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Пациент')
        verbose_name_plural = _('Пациенты')
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return self.user.get_full_name()

    def get_absolute_url(self):
        return reverse('patient_detail', kwargs={'pk': self.pk})

    @property
    def age(self):
        today = timezone.now().date()
        return (today - self.birth_date).days // 365

    def clean(self):
        if self.age < 18:
            raise ValidationError(_('Пациент должен быть старше 18 лет'))

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', _('Запланирован')),
        ('completed', _('Завершен')),
        ('canceled', _('Отменен')),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT,
        verbose_name=_('Врач')
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        verbose_name=_('Пациент')
    )
    date = models.DateField(_('Дата приема'))
    time = models.TimeField(_('Время приема'))
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    notes = models.TextField(
        _('Заметки пациента'),
        blank=True,
        help_text=_('Симптомы, жалобы и т.д.')
    )
    diagnosis = models.TextField(
        _('Диагноз'),
        blank=True
    )
    prescription = models.TextField(
        _('Назначение'),
        blank=True
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Запись на прием')
        verbose_name_plural = _('Записи на прием')
        ordering = ['-date', '-time']
        unique_together = ['doctor', 'date', 'time']

    def __str__(self):
        return f"{self.patient} -> {self.doctor} на {self.date} {self.time}"

    def get_absolute_url(self):
        return reverse('appointment_detail', kwargs={'pk': self.pk})

    def clean(self):
        if self.date < timezone.now().date():
            raise ValidationError(_('Нельзя записаться на прошедшую дату'))

        if self.time.hour < 9 or self.time.hour >= 18:
            raise ValidationError(_('Приемы проводятся с 9:00 до 18:00'))

        if self.status == 'scheduled' and self.pk:
            conflicting_appointments = Appointment.objects.filter(
                doctor=self.doctor,
                date=self.date,
                time=self.time,
                status='scheduled'
            ).exclude(pk=self.pk)
            
            if conflicting_appointments.exists():
                raise ValidationError(_('Выбранное время уже занято другим пациентом'))

    @property
    def datetime(self):
        return timezone.datetime.combine(self.date, self.time)

    @property
    def is_past_due(self):
        return self.datetime < timezone.now()

    @property
    def duration(self):
        return timedelta(minutes=30) 

class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 - Ужасно'),
        (2, '2 - Плохо'),
        (3, '3 - Удовлетворительно'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        verbose_name=_('Врач')
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        verbose_name=_('Пациент')
    )
    rating = models.PositiveSmallIntegerField(
        _('Оценка'),
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(
        _('Комментарий'),
        blank=True
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Запись на прием')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')
        ordering = ['-created_at']
        unique_together = ['doctor', 'patient', 'appointment']

    def __str__(self):
        return f"Отзыв {self.patient} о {self.doctor} ({self.rating})"

    def get_absolute_url(self):
        return reverse('review_detail', kwargs={'pk': self.pk})

    @property
    def rating_stars(self):
        return '★' * self.rating + '☆' * (5 - self.rating)

class MedicalDocument(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        verbose_name=_('Пациент')
    )
    file = models.FileField(
        _('Файл'),
        upload_to=document_upload_path,
        help_text=_('PDF, JPG или PNG (макс. 5MB)')
    )
    uploaded_at = models.DateTimeField(_('Дата загрузки'), auto_now_add=True)

    class Meta:
        verbose_name = _('Медицинский документ')
        verbose_name_plural = _('Медицинские документы')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Документ {self.patient} от {self.uploaded_at.strftime('%d.%m.%Y')}"

    def clean(self):
        if self.file:
            if self.file.size > 5 * 1024 * 1024:
                raise ValidationError(_('Файл слишком большой. Максимальный размер - 5MB'))
            
            ext = os.path.splitext(self.file.name)[1][1:].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise ValidationError(_('Неподдерживаемый формат файла. Разрешены: PDF, JPG, PNG'))

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def filesize(self):
        size = self.file.size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    @property
    def filetype(self):
        ext = os.path.splitext(self.file.name)[1][1:].lower()
        return ext.upper()