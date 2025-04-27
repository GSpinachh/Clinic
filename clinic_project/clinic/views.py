from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, 
    TemplateView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.urls import reverse_lazy
from django.template.loader import get_template
from django.db.models import Q, Count, Avg
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import datetime, timedelta, date
from xhtml2pdf import pisa
from io import BytesIO
import os

from .models import (
    Specialty, Doctor, Patient, 
    Appointment, Review, MedicalDocument
)
from .forms import (
    UserRegistrationForm, ProfileForm, AppointmentForm,
    ReviewForm, MedicalDocumentForm, PatientProfileForm
)

class HomeView(TemplateView):
    template_name = 'clinic/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specialties'] = Specialty.objects.annotate(
            doctor_count=Count('doctor', filter=Q(doctor__is_active=True))
        ).order_by('name')
        context['popular_doctors'] = Doctor.objects.filter(
            is_active=True
        ).annotate(
            review_count=Count('review')
        ).order_by('-review_count')[:4]
        return context

class DoctorListView(ListView):
    model = Doctor
    template_name = 'clinic/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 10

    def get_queryset(self):
        queryset = Doctor.objects.filter(
            is_active=True
        ).select_related(
            'user', 'specialty'
        ).annotate(
            avg_rating=Avg('review__rating'),
            review_count=Count('review')
        )

        specialty_slug = self.kwargs.get('specialty_slug')
        if specialty_slug:
            queryset = queryset.filter(specialty__slug=specialty_slug)

        sort = self.request.GET.get('sort')
        if sort == 'rating':
            queryset = queryset.order_by('-avg_rating')
        elif sort == 'experience':
            queryset = queryset.order_by('-experience')
        else:
            queryset = queryset.order_by('user__last_name')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specialties'] = Specialty.objects.all()
        context['selected_specialty'] = self.kwargs.get('specialty_slug')
        return context

class DoctorDetailView(DetailView):
    model = Doctor
    template_name = 'clinic/doctor_detail.html'
    context_object_name = 'doctor'

    def get_queryset(self):
        return Doctor.objects.filter(
            is_active=True
        ).select_related(
            'user', 'specialty'
        ).annotate(
            avg_rating=Avg('review__rating'),
            review_count=Count('review')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object
        
        reviews = doctor.review_set.all().select_related(
            'patient__user'
        ).order_by('-created_at')
        
        if self.request.user.is_authenticated and hasattr(self.request.user, 'patient'):
            context['user_review'] = reviews.filter(
                patient=self.request.user.patient
            ).first()
        
        context['reviews'] = reviews[:5]
        context['available_dates'] = self.get_available_dates(doctor)
        
        return context

    def get_available_dates(self, doctor):
        """Возвращает список доступных дат для записи на 2 недели вперед"""
        today = timezone.now().date()
        dates = []
        
        for day in range(14):
            current_date = today + timedelta(days=day)
            if current_date.weekday() < 5:  
                if doctor.get_available_slots(current_date):
                    dates.append(current_date)
        
        return dates

class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'clinic/appointment_create.html'

    def get_success_url(self):
        return reverse_lazy('appointment_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        doctor_id = self.kwargs.get('doctor_id')
        if doctor_id:
            kwargs['initial'] = {'doctor': doctor_id}
        
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        doctor_id = self.kwargs.get('doctor_id')
        if doctor_id:
            context['doctor'] = get_object_or_404(Doctor, pk=doctor_id)
            
            today = timezone.now().date()
            available_dates = []
            
            for day in range(14):
                current_date = today + timedelta(days=day)
                if current_date.weekday() < 5:
                    available_dates.append(current_date)
            
            context['available_dates'] = available_dates
        
        return context

    def form_valid(self, form):
        form.instance.patient = self.request.user.patient
        messages.success(self.request, 'Запись успешно создана!')
        return super().form_valid(form)

class AppointmentListView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'clinic/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 10

    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user.patient
        ).select_related(
            'doctor__user', 'doctor__specialty'
        ).order_by('-date', '-time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        appointments = self.get_queryset()
        
        context['upcoming_appointments'] = appointments.filter(
            date__gte=timezone.now().date(),
            status='scheduled'
        )
        
        context['completed_appointments'] = appointments.filter(
            Q(date__lt=timezone.now().date()) | 
            Q(status__in=['completed', 'canceled'])
        ).order_by('-date', '-time')
        
        return context

class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = 'clinic/appointment_detail.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return Appointment.objects.select_related(
            'doctor__user', 'doctor__specialty',
            'patient__user'
        )

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.patient.user != request.user and not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.object
        
        if hasattr(self.request.user, 'patient'):
            context['has_review'] = Review.objects.filter(
                doctor=appointment.doctor,
                patient=self.request.user.patient,
                appointment=appointment
            ).exists()
        
        return context

class AppointmentCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        
        if appointment.patient.user != request.user:
            raise PermissionDenied
        
        if appointment.status == 'scheduled':
            appointment.status = 'canceled'
            appointment.save()
            messages.success(request, 'Запись успешно отменена')
        else:
            messages.error(request, 'Невозможно отменить эту запись')
        
        return redirect('appointment_list')

class AppointmentPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        
        if appointment.patient.user != request.user and not request.user.is_staff:
            raise PermissionDenied
        
        template = get_template('clinic/appointment_pdf.html')
        context = {'appointment': appointment}
        html = template.render(context)
        
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"Справка_{appointment.date.strftime('%Y-%m-%d')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        return HttpResponse('Ошибка при генерации PDF', status=500)

class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = 'clinic/review_form.html'

    def get_success_url(self):
        return reverse_lazy('doctor_detail', kwargs={'pk': self.object.doctor.pk})

    def get_initial(self):
        initial = super().get_initial()
        doctor_id = self.kwargs.get('pk')
        initial['doctor'] = get_object_or_404(Doctor, pk=doctor_id)
        
        appointment_id = self.request.GET.get('appointment')
        if appointment_id:
            appointment = get_object_or_404(
                Appointment, 
                pk=appointment_id,
                patient=self.request.user.patient
            )
            initial['appointment'] = appointment
        
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = get_object_or_404(Doctor, pk=self.kwargs.get('pk'))
        return context

    def form_valid(self, form):
        form.instance.patient = self.request.user.patient
        messages.success(self.request, 'Спасибо за ваш отзыв!')
        return super().form_valid(form)

class UserRegistrationView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Регистрация прошла успешно! Теперь вы можете войти.'
        )
        return response

class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'registration/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if hasattr(self.request.user, 'patient'):
            context['patient_form'] = PatientProfileForm(
                instance=self.request.user.patient
            )
            context['documents'] = MedicalDocument.objects.filter(
                patient=self.request.user.patient
            ).order_by('-uploaded_at')
        
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if hasattr(request.user, 'patient'):
            patient_form = PatientProfileForm(
                request.POST, 
                request.FILES,
                instance=request.user.patient
            )
            
            if form.is_valid() and patient_form.is_valid():
                return self.form_valid(form, patient_form)
            else:
                return self.form_invalid(form, patient_form)
        else:
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

    def form_valid(self, form, patient_form=None):
        response = super().form_valid(form)
        
        if patient_form:
            patient_form.save()
            messages.success(self.request, 'Профиль успешно обновлен')
        
        return response

    def form_invalid(self, form, patient_form=None):
        context = self.get_context_data(form=form)
        
        if patient_form:
            context['patient_form'] = patient_form
        
        return self.render_to_response(context)

class GetDoctorsView(View):
    def get(self, request):
        specialty_id = request.GET.get('specialty_id')
        if not specialty_id:
            return JsonResponse([], safe=False)
            
        doctors = Doctor.objects.filter(
            specialty_id=specialty_id,
            is_active=True
        ).select_related('user')
        
        data = [
            {
                'id': doctor.id,
                'name': doctor.user.get_full_name(),
                'photo_url': request.build_absolute_uri(doctor.photo.url) if doctor.photo else None,
                'specialty': doctor.specialty.name
            }
            for doctor in doctors
        ]
        
        return JsonResponse(data, safe=False)

class GetAvailableDatesView(View):
    def get(self, request, doctor_id):
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        today = date.today()
        dates = []
        
        for day in range(14):
            current_date = today + timedelta(days=day)
            if current_date.weekday() < 5:
                if doctor.get_available_slots(current_date):
                    dates.append(current_date.strftime('%Y-%m-%d'))
        
        return JsonResponse({'dates': dates})

class GetAvailableTimesView(View):
    def get(self, request, doctor_id, date_str):
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
        
        available_slots = doctor.get_available_slots(selected_date)
        times = [slot.strftime('%H:%M') for slot in available_slots]
        
        return JsonResponse({'times': times})

@login_required
def upload_document(request):
    if request.method == 'POST' and request.FILES:
        form = MedicalDocumentForm(request.POST, request.FILES)
        
        if form.is_valid() and hasattr(request.user, 'patient'):
            document = form.save(commit=False)
            document.patient = request.user.patient
            document.save()
            messages.success(request, 'Документ успешно загружен')
        else:
            messages.error(request, 'Ошибка при загрузке документа')
    
    return redirect('profile')

@login_required
def delete_document(request, pk):
    if request.method == 'POST' and hasattr(request.user, 'patient'):
        document = get_object_or_404(
            MedicalDocument, 
            pk=pk,
            patient=request.user.patient
        )
        document.delete()
        messages.success(request, 'Документ удален')
    
    return redirect('profile')

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)