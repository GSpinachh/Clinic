from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    HomeView, DoctorListView, DoctorDetailView,
    AppointmentCreateView, AppointmentListView, AppointmentDetailView,
    ReviewCreateView, ProfileView, UserRegistrationView,
    AppointmentCancelView, AppointmentPDFView, DoctorScheduleView
)

app_name = 'clinic'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    
    path('accounts/register/', UserRegistrationView.as_view(), name='register'),
    path('accounts/profile/', ProfileView.as_view(), name='profile'),
    path('accounts/password_change/', 
         auth_views.PasswordChangeView.as_view(
             template_name='registration/password_change.html',
             success_url='/accounts/profile/'
         ), 
         name='password_change'),
    
    path('doctors/', DoctorListView.as_view(), name='doctor_list'),
    path('doctors/schedule/', DoctorScheduleView.as_view(), name='doctor_schedule'),
    path('doctors/<int:pk>/', DoctorDetailView.as_view(), name='doctor_detail'),
    path('doctors/<int:pk>/review/', ReviewCreateView.as_view(), name='create_review'),
    path('doctors/specialty/<slug:specialty_slug>/', 
         DoctorListView.as_view(), 
         name='doctor_list_by_specialty'),
    
    path('appointments/', AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/create/', 
         AppointmentCreateView.as_view(), 
         name='appointment_create'),
    path('appointments/create/<int:doctor_id>/', 
         AppointmentCreateView.as_view(), 
         name='appointment_create_with_doctor'),
    path('appointments/<int:pk>/', 
         AppointmentDetailView.as_view(), 
         name='appointment_detail'),
    path('appointments/<int:pk>/cancel/', 
         AppointmentCancelView.as_view(), 
         name='appointment_cancel'),
    path('appointments/<int:pk>/pdf/', 
         AppointmentPDFView.as_view(), 
         name='appointment_pdf'),
    
    path('api/doctors/', views.DoctorListAPIView.as_view(), name='api_doctor_list'),
    path('api/doctors/<int:pk>/available-slots/', 
         views.DoctorAvailableSlotsAPIView.as_view(), 
         name='api_doctor_slots'),
    path('api/appointments/', 
         views.AppointmentListCreateAPIView.as_view(), 
         name='api_appointment_list'),
    
    path('get-doctors/', views.GetDoctorsView.as_view(), name='get_doctors'),
    path('get-available-dates/<int:doctor_id>/', 
         views.GetAvailableDatesView.as_view(), 
         name='get_available_dates'),
    path('get-available-times/<int:doctor_id>/<str:date>/', 
         views.GetAvailableTimesView.as_view(), 
         name='get_available_times'),
    
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/<int:pk>/delete/', views.delete_document, name='delete_document'),
]

handler404 = 'clinic.views.handler404'
handler500 = 'clinic.views.handler500'