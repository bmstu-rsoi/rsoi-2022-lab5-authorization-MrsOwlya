from django.urls import path, include
from . import views

urlpatterns = [
    path('tickets', views.user_tickets_or_buy),
    path('tickets/<uuid:ticketId>', views.user_ticket_info_or_cancel),
    path('flights', views.flights_list),
    path('me', views.user_info),
    path('privilege', views.privilege_info),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("callback", views.callback, name="callback"),
]