"""URL poti za aplikacijo groups."""

from django.urls import path

from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list, name='list'),
    path('moje/', views.my_groups, name='my_groups'),
    path('nova/', views.create_group, name='create'),
    path('<slug:slug>/', views.group_detail, name='detail'),
    path('<slug:slug>/uredi/', views.edit_group, name='edit'),
    path('<slug:slug>/pridruzi/', views.join_group, name='join'),
    path('<slug:slug>/zapusti/', views.leave_group, name='leave'),
    path('<slug:slug>/odobri/<int:user_id>/', views.approve_member, name='approve'),
    path('<slug:slug>/zavrni/<int:user_id>/', views.reject_member, name='reject'),
]
