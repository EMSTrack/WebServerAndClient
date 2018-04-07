import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.generic import TemplateView, ListView, \
    DetailView, CreateView, UpdateView

from .models import Ambulance, AmbulanceCapability, AmbulanceStatus, \
    Call, Location, LocationType

from .forms import AmbulanceCreateForm, AmbulanceUpdateForm, LocationAdminCreateForm, LocationAdminUpdateForm

from emstrack.mixins import BasePermissionMixin, UpdatedByMixin

from emstrack.views import get_page_links, get_page_size_links


# Ambulance views

class AmbulancePermissionMixin(BasePermissionMixin):

    filter_field = 'id'
    profile_field = 'ambulances'
    queryset = Ambulance.objects.all()


class AmbulanceDetailView(LoginRequiredMixin,
                          SuccessMessageMixin,
                          UpdatedByMixin,
                          AmbulancePermissionMixin,
                          DetailView):

    model = Ambulance
    
    def get_context_data(self, **kwargs):

        # add paginated updates to context

        # call supper
        context = super().get_context_data(**kwargs)

        # query
        updates_query = self.object.ambulanceupdate_set.order_by('-timestamp')

        # get current page
        page = self.request.GET.get('page', 1)
        page_size = self.request.GET.get('page_size', 250)
        page_sizes = [250, 500, 1000]

        # paginate
        paginator = Paginator(updates_query, page_size)
        try:
            updates = paginator.page(page)
        except PageNotAnInteger:
            updates = paginator.page(1)
        except EmptyPage:
            updates = paginator.page(paginator.num_pages)

        context['updates'] = updates
        context['page_links'] = get_page_links(self.request, updates)
        context['page_size_links'] = get_page_size_links(self.request, updates, page_sizes)
        context['page_size'] = int(page_size)

        # add ambulance_status
        context['ambulance_status'] = {m.name: m.value
                                       for m in AmbulanceStatus}

        return context


class AmbulanceListView(LoginRequiredMixin,
                        AmbulancePermissionMixin,
                        ListView):
    
    model = Ambulance
    ordering = ['identifier']


class AmbulanceCreateView(LoginRequiredMixin,
                          SuccessMessageMixin,
                          UpdatedByMixin,
                          AmbulancePermissionMixin,
                          CreateView):
    
    model = Ambulance
    form_class = AmbulanceCreateForm

    def get_success_url(self):
        return self.object.get_absolute_url()
    

class AmbulanceUpdateView(LoginRequiredMixin,
                          SuccessMessageMixin,
                          UpdatedByMixin,
                          AmbulancePermissionMixin,
                          UpdateView):
    
    model = Ambulance
    form_class = AmbulanceUpdateForm

    def get_success_url(self):
        return self.object.get_absolute_url()


class AmbulanceMap(TemplateView):
    template_name = 'ambulance/map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ambulance_status'] = {m.name: m.value
                                       for m in AmbulanceStatus}
        context['ambulance_capability'] = {m.name: m.value
                                           for m in AmbulanceCapability}
        context['location_type'] = {m.name: m.value
                                    for m in LocationType}
        context['broker_websockets_host'] = settings.MQTT['BROKER_WEBSOCKETS_HOST']
        context['broker_websockets_port'] = settings.MQTT['BROKER_WEBSOCKETS_PORT']
        context['client_id'] = 'javascript_client_' + uuid.uuid4().hex
        return context


# Locations

class LocationAdminListView(ListView):
    model = Location


class LocationAdminDetailView(DetailView):
    model = Location


class LocationAdminCreateView(SuccessMessageMixin,
                              UpdatedByMixin,
                              CreateView):
    model = Location
    form_class = LocationAdminCreateForm

    def get_success_message(self, cleaned_data):
        return "Successfully created location '{}'".format(cleaned_data['name'])

    def get_success_url(self):
        return self.object.get_absolute_url()


class LocationAdminUpdateView(SuccessMessageMixin,
                              UpdatedByMixin,
                              UpdateView):
    model = Location
    form_class = LocationAdminUpdateForm

    def get_success_message(self, cleaned_data):
        return "Successfully updated location '{}'".format(cleaned_data['name'])

    def get_success_url(self):
        return self.object.get_absolute_url()

# Call ListView
class CallListView(ListView):
    model = Call
    template_name = 'ambulance/call_list.html'


# Admin page
class AdminView(ListView):
    model = Call
    template_name = 'ambulance/dispatch_list.html'
    context_object_name = "ambulance_call"


# # AmbulanceStatus list page
# class AmbulanceStatusCreateView(CreateView):
#     model = AmbulanceStatus
#     context_object_name = "ambulance_status_form"
#     form_class = AmbulanceStatusCreateForm
#     success_url = reverse_lazy('status')

#     def get_context_data(self, **kwargs):
#         context = super(AmbulanceStatusCreateView, self).get_context_data(**kwargs)
#         context['statuses'] = AmbulanceStatus.objects.all().order_by('id')
#         return context


# # AmbulanceStatus update page
# class AmbulanceStatusUpdateView(UpdateView):
#     model = AmbulanceStatus
#     form_class = AmbulanceStatusUpdateForm
#     template_name = 'ambulances/ambulance_status_edit.html'
#     success_url = reverse_lazy('status')

#     def get_object(self, queryset=None):
#         obj = AmbulanceStatus.objects.get(id=self.kwargs['pk'])
#         return obj

#     def get_context_data(self, **kwargs):
#         context = super(AmbulanceStatusUpdateView, self).get_context_data(**kwargs)
#         context['id'] = self.kwargs['pk']
#         return context


# # Ambulance map page
# class AmbulanceMap(views.JSONResponseMixin, views.AjaxResponseMixin, ListView):
#     template_name = 'ambulances/ambulance_map.html'

#     def get_queryset(self):
#         return Ambulance.objects.all()
