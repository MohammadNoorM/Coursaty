from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('courses/', views.course_list_view, name='course_list'),
    path('courses/<slug:slug>/', views.course_detail_view, name='course_detail'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('courses/<slug:course_slug>/lessons/<slug:lesson_slug>/', views.lesson_view, name='lesson'),
    path('lessons/<int:lesson_id>/comment/', views.add_comment, name='add_comment'),
    path('courses/<slug:course_slug>/wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
]
