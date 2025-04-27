from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Doctor, Patient, Appointment, Review, MedicalDocument
from datetime import date

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.com'})
    )
    first_name = forms.CharField(
        label=_("Имя"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label=_("Фамилия"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        label=_("Телефон"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'})
    )
    birth_date = forms.DateField(
        label=_("Дата рождения"),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text=_("Формат: ДД.ММ.ГГГГ")
    )
    address = forms.CharField(
        label=_("Адрес"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_birth_date(self):
        birth_date = self.cleaned_data['birth_date']
        age = (date.today() - birth_date).days // 365
        if age < 18:
            raise ValidationError(_("Пациент должен быть старше 18 лет"))
        return birth_date

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError(_("Пользователь с таким email уже существует"))
        return email

class ProfileUpdateForm(UserChangeForm):
    password = None 

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['phone', 'birth_date', 'address', 'medical_history', 'photo']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['specialty', 'bio', 'education', 'experience', 'photo', 'is_active']
        widgets = {
            'specialty': forms.Select(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'experience': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class AppointmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'patient'):
            self.fields['patient'].initial = user.patient
            self.fields['patient'].widget = forms.HiddenInput()
        
        if 'specialty' in self.data:
            try:
                specialty_id = int(self.data.get('specialty'))
                self.fields['doctor'].queryset = Doctor.objects.filter(
                    specialty_id=specialty_id,
                    is_active=True
                ).order_by('user__last_name')
            except (ValueError, TypeError):
                pass

    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text=_("Выберите дату приема")
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        help_text=_("Выберите время приема")
    )

    class Meta:
        model = Appointment
        fields = ['specialty', 'doctor', 'patient', 'date', 'time', 'notes']
        widgets = {
            'specialty': forms.Select(attrs={'class': 'form-control', 'id': 'id_specialty'}),
            'doctor': forms.Select(attrs={'class': 'form-control', 'id': 'id_doctor'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        doctor = cleaned_data.get('doctor')

        if date and time and doctor:
            if Appointment.objects.filter(
                doctor=doctor,
                date=date,
                time=time,
                status='scheduled'
            ).exists():
                raise ValidationError(_("Выбранное время уже занято. Пожалуйста, выберите другое время."))

            if date < date.today():
                raise ValidationError(_("Нельзя записаться на прошедшую дату"))

            # с 9 до 18
            if time.hour < 9 or time.hour >= 18:
                raise ValidationError(_("Приемы проводятся с 9:00 до 18:00"))

        return cleaned_data

class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [
        (1, '1 - Плохо'),
        (2, '2 - Удовлетворительно'),
        (3, '3 - Нормально'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'rating-radio'}),
        label=_("Оценка")
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label=_("Комментарий"),
        required=False
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']

class MedicalDocumentForm(forms.ModelForm):
    class Meta:
        model = MedicalDocument
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # max 5MB
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(_("Файл слишком большой. Максимальный размер - 5MB"))
            
            ext = file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise ValidationError(_("Неподдерживаемый формат файла. Разрешены: PDF, JPG, PNG"))
        
        return file

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label=_("Старый пароль"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password1 = forms.CharField(
        label=_("Новый пароль"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label=_("Подтверждение нового пароля"),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class AppointmentStatusForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class AppointmentResultsForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['diagnosis', 'prescription']
        widgets = {
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'prescription': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }