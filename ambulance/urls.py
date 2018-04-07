from django.conf.urls import url
from django.contrib.admin.views.decorators import staff_member_required

from django.contrib.auth.decorators import login_required

from . import views

app_name = 'ambulance'
urlpatterns = [
    
    url(r'^map/$',
        login_required(views.AmbulanceMap.as_view()),
        name="map"),
    
    url(r'^list/$',
        login_required(views.AmbulanceListView.as_view()),
        name="list"),
    
    url(r'^create/$',
        login_required(views.AmbulanceCreateView.as_view()),
        name='create'),
    
    url(r'^detail/(?P<pk>[0-9]+)$',
        login_required(views.AmbulanceDetailView.as_view()),
        name='detail'),

    url(r'^update/(?P<pk>[0-9]+)$',
        login_required(views.AmbulanceUpdateView.as_view()),
        name='update'),

    # Admin

    url(r'^location/list/$',
        staff_member_required(views.LocationAdminListView.as_view()),
        name='location_list'),

    url(r'^location/create$',
        staff_member_required(views.LocationAdminCreateView.as_view()),
        name='location_create'),

    url(r'^location/detail/(?P<pk>[0-9]+)$',
        staff_member_required(views.LocationAdminDetailView.as_view()),
        name='location_detail'),

    url(r'^location/update/(?P<pk>[0-9]+)$',
        staff_member_required(views.LocationAdminUpdateView.as_view()),
        name='location_update'),

    # NEED REVISING
    
    url(r'^call/list/$',
        login_required(views.CallListView.as_view()),
        name="call_list"),

    url(r'^admin/$',
        login_required(views.AdminView.as_view()),
        name="admin"),
    
]
