from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from .models import (
    User, Specialty, Doctor, Patient, 
    Appointment, Review, MedicalDocument
)

# Отмена регистрации User
admin.site.unregister(User)

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'doctor_count', 'avg_rating')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _doctor_count=Count('doctor', distinct=True),
            _avg_rating=Avg('doctor__review__rating')
        )
        return queryset
    
    def doctor_count(self, obj):
        return obj._doctor_count
    doctor_count.short_description = 'Кол-во врачей'
    doctor_count.admin_order_field = '_doctor_count'
    
    def avg_rating(self, obj):
        return round(obj._avg_rating, 2) if obj._avg_rating else 'Нет отзывов'
    avg_rating.short_description = 'Средний рейтинг'
    avg_rating.admin_order_field = '_avg_rating'

class MedicalDocumentInline(admin.TabularInline):
    model = MedicalDocument
    extra = 0
    readonly_fields = ('file_link', 'uploaded_at')
    fields = ('file_link', 'uploaded_at', 'file')
    
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Просмотр</a> | '
                '<a href="{}" download>Скачать</a>',
                obj.file.url,
                obj.file.url
            )
        return "-"
    file_link.short_description = "Действия"

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'phone', 'birth_date', 'document_count')
    list_filter = ('birth_date',)
    search_fields = (
        'user__first_name', 
        'user__last_name', 
        'user__email',
        'phone'
    )
    inlines = [MedicalDocumentInline]
    readonly_fields = ('user_link', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('user_link', 'phone', 'birth_date', 'address')
        }),
        ('Дополнительно', {
            'fields': ('medical_history', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('user').annotate(
            _document_count=Count('medicaldocument', distinct=True)
        )
        return queryset
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.user.last_name,
            obj.user.first_name
        )
    user_link.short_description = 'Пациент'
    user_link.admin_order_field = 'user__last_name'
    
    def document_count(self, obj):
        return obj._document_count
    document_count.short_description = 'Документов'
    document_count.admin_order_field = '_document_count'

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('patient_link', 'rating_stars', 'created_at')
    fields = ('patient_link', 'rating_stars', 'comment', 'created_at')
    
    def patient_link(self, obj):
        url = reverse('admin:clinic_patient_change', args=[obj.patient.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.patient.user.last_name,
            obj.patient.user.first_name
        )
    patient_link.short_description = 'Пациент'
    
    def rating_stars(self, obj):
        return format_html(
            '<span style="color: #ffc107;">{}</span>',
            '★' * obj.rating + '☆' * (5 - obj.rating)
        )
    rating_stars.short_description = 'Рейтинг'

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = (
        'user_link', 
        'specialty_link', 
        'experience', 
        'review_count',
        'avg_rating',
        'is_active'
    )
    list_filter = ('specialty', 'is_active')
    search_fields = (
        'user__first_name', 
        'user__last_name', 
        'user__email',
        'specialty__name'
    )
    list_editable = ('is_active',)
    inlines = [ReviewInline]
    readonly_fields = ('user_link', 'photo_preview', 'created_at')
    fieldsets = (
        (None, {
            'fields': ('user_link', 'specialty', 'is_active')
        }),
        ('Информация', {
            'fields': ('photo', 'photo_preview', 'bio', 'education', 'experience')
        }),
        ('Дополнительно', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('user', 'specialty').annotate(
            _review_count=Count('review', distinct=True),
            _avg_rating=Avg('review__rating')
        )
        return queryset
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.user.last_name,
            obj.user.first_name
        )
    user_link.short_description = 'Врач'
    user_link.admin_order_field = 'user__last_name'
    
    def specialty_link(self, obj):
        url = reverse('admin:clinic_specialty_change', args=[obj.specialty.id])
        return format_html('<a href="{}">{}</a>', url, obj.specialty.name)
    specialty_link.short_description = 'Специальность'
    specialty_link.admin_order_field = 'specialty__name'
    
    def review_count(self, obj):
        return obj._review_count
    review_count.short_description = 'Отзывов'
    review_count.admin_order_field = '_review_count'
    
    def avg_rating(self, obj):
        return round(obj._avg_rating, 2) if obj._avg_rating else 'Нет отзывов'
    avg_rating.short_description = 'Средний рейтинг'
    avg_rating.admin_order_field = '_avg_rating'
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 200px;" />',
                obj.photo.url
            )
        return "Нет фото"
    photo_preview.short_description = 'Предпросмотр фото'

class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'date_time',
        'doctor_link',
        'patient_link',
        'status_badge',
        'has_diagnosis'
    )
    list_filter = ('status', 'date', 'doctor__specialty')
    search_fields = (
        'doctor__user__first_name',
        'doctor__user__last_name',
        'patient__user__first_name',
        'patient__user__last_name'
    )
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'
    list_per_page = 20
    fieldsets = (
        (None, {
            'fields': ('doctor', 'patient', 'status')
        }),
        ('Детали приема', {
            'fields': ('date', 'time', 'notes')
        }),
        ('Результаты', {
            'fields': ('diagnosis', 'prescription'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'doctor__user', 
            'patient__user'
        )
        return queryset
    
    def date_time(self, obj):
        return f"{obj.date.strftime('%d.%m.%Y')} {obj.time.strftime('%H:%M')}"
    date_time.short_description = 'Дата и время'
    date_time.admin_order_field = 'date'
    
    def doctor_link(self, obj):
        url = reverse('admin:clinic_doctor_change', args=[obj.doctor.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.doctor.user.last_name,
            obj.doctor.user.first_name
        )
    doctor_link.short_description = 'Врач'
    doctor_link.admin_order_field = 'doctor__user__last_name'
    
    def patient_link(self, obj):
        url = reverse('admin:clinic_patient_change', args=[obj.patient.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.patient.user.last_name,
            obj.patient.user.first_name
        )
    patient_link.short_description = 'Пациент'
    patient_link.admin_order_field = 'patient__user__last_name'
    
    def status_badge(self, obj):
        colors = {
            'scheduled': 'bg-primary',
            'completed': 'bg-success',
            'canceled': 'bg-danger'
        }
        return format_html(
            '<span class="badge {}">{}</span>',
            colors.get(obj.status, 'bg-secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def has_diagnosis(self, obj):
        return bool(obj.diagnosis)
    has_diagnosis.short_description = 'Есть диагноз'
    has_diagnosis.boolean = True

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'doctor_link',
        'patient_link',
        'rating_stars',
        'created_at',
        'has_appointment'
    )
    list_filter = ('rating', 'created_at', 'doctor__specialty')
    search_fields = (
        'doctor__user__first_name',
        'doctor__user__last_name',
        'patient__user__first_name',
        'patient__user__last_name'
    )
    readonly_fields = ('created_at', 'rating_stars')
    date_hierarchy = 'created_at'
    
    def doctor_link(self, obj):
        url = reverse('admin:clinic_doctor_change', args=[obj.doctor.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.doctor.user.last_name,
            obj.doctor.user.first_name
        )
    doctor_link.short_description = 'Врач'
    doctor_link.admin_order_field = 'doctor__user__last_name'
    
    def patient_link(self, obj):
        url = reverse('admin:clinic_patient_change', args=[obj.patient.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.patient.user.last_name,
            obj.patient.user.first_name
        )
    patient_link.short_description = 'Пациент'
    patient_link.admin_order_field = 'patient__user__last_name'
    
    def rating_stars(self, obj):
        return format_html(
            '<span style="color: #ffc107;">{}</span>',
            '★' * obj.rating + '☆' * (5 - obj.rating)
        )
    rating_stars.short_description = 'Рейтинг'
    
    def has_appointment(self, obj):
        return bool(obj.appointment)
    has_appointment.short_description = 'По записи'
    has_appointment.boolean = True

@admin.register(MedicalDocument)
class MedicalDocumentAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'file_link', 'uploaded_at', 'file_size')
    list_filter = ('uploaded_at',)
    search_fields = (
        'patient__user__first_name',
        'patient__user__last_name',
        'file'
    )
    readonly_fields = ('file_link', 'uploaded_at', 'file_size')
    date_hierarchy = 'uploaded_at'
    
    def patient_link(self, obj):
        url = reverse('admin:clinic_patient_change', args=[obj.patient.id])
        return format_html(
            '<a href="{}">{} {}</a>',
            url,
            obj.patient.user.last_name,
            obj.patient.user.first_name
        )
    patient_link.short_description = 'Пациент'
    patient_link.admin_order_field = 'patient__user__last_name'
    
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Просмотр</a> | '
                '<a href="{}" download>Скачать</a>',
                obj.file.url,
                obj.file.url
            )
        return "-"
    file_link.short_description = "Файл"
    
    def file_size(self, obj):
        if obj.file:
            return f"{obj.file.size / 1024:.1f} KB"
        return "-"
    file_size.short_description = "Размер"

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    actions = ['make_doctor', 'make_patient']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related('doctor', 'patient')
        return queryset
    
    def user_type(self, obj):
        if hasattr(obj, 'doctor'):
            return 'Врач'
        elif hasattr(obj, 'patient'):
            return 'Пациент'
        return 'Персонал'
    user_type.short_description = 'Тип пользователя'
    
    def make_doctor(self, request, queryset):
        for user in queryset:
            if not hasattr(user, 'doctor'):
                Doctor.objects.create(user=user, specialty=Specialty.objects.first())
        self.message_user(request, "Выбранные пользователи назначены врачами")
    make_doctor.short_description = "Сделать врачами"
    
    def make_patient(self, request, queryset):
        for user in queryset:
            if not hasattr(user, 'patient'):
                Patient.objects.create(user=user)
        self.message_user(request, "Выбранные пользователи назначены пациентами")
    make_patient.short_description = "Сделать пациентами" 

admin.site.register(User, CustomUserAdmin)
admin.site.register(Appointment, AppointmentAdmin) 