import logging
import random
import string
from datetime import timedelta

from braces.views import CsrfExemptMixin
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http.response import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.views.generic.base import View
from django.views.generic.detail import BaseDetailView
from django.views.generic.edit import FormView, CreateView
from drf_extra_fields.geo_fields import PointField
from extra_views import InlineFormSet, CreateWithInlinesView, UpdateWithInlinesView
from rest_framework.response import Response
from rest_framework.views import APIView

from ambulance.models import AmbulanceStatus, AmbulanceCapability, LocationType, Call, CallStatus, AmbulanceCallStatus, \
    AmbulanceStatusOrder, AmbulanceCapabilityOrder, CallPriority, CallPriorityOrder, CallStatusOrder, LocationTypeOrder, \
    WaypointStatus
from emstrack import CURRENT_VERSION, MINIMUM_VERSION
from emstrack.mixins import SuccessMessageWithInlinesMixin, UpdatedByMixin
from emstrack.models import defaults
from emstrack.views import get_page_links, get_page_size_links
from equipment.models import EquipmentType, EquipmentTypeDefaults
from mqtt.cache_clear import mqtt_cache_clear
from .forms import MQTTAuthenticationForm, AuthenticationForm, SignupForm, \
    UserAdminCreateForm, UserAdminUpdateForm, \
    GroupAdminUpdateForm, \
    GroupProfileAdminForm, GroupAmbulancePermissionAdminForm, GroupHospitalPermissionAdminForm, \
    UserAmbulancePermissionAdminForm, \
    UserHospitalPermissionAdminForm, RestartForm, UserProfileAdminForm
from .models import TemporaryPassword, \
    UserAmbulancePermission, UserHospitalPermission, \
    GroupProfile, GroupAmbulancePermission, \
    GroupHospitalPermission, Client, ClientStatus, UserProfile
from .permissions import get_permissions

logger = logging.getLogger(__name__)


# signup

class SignupView(FormView):
    template_name = 'index.html'
    form_class = SignupForm

    def form_valid(self, form):
        # TODO: Automatic signup could send an email to prospective user
        # then notify administrator of new user
        # form.send_email()
        # return super().form_valid(form)
        # for now abort and alert user
        form.add_error(None, 'We are sorry but EMSTrack is not accepting new users at this point.');
        return super().form_invalid(form);


# login

class LoginView(auth_views.LoginView):
    template_name = 'index.html'
    authentication_form = AuthenticationForm

    def form_valid(self, form):

        result = super(LoginView, self).form_valid(form)

        # get user
        user = self.request.user

        # if user is dispatcher set session to expire in 14 days
        if user.is_superuser or user.is_staff or user.userprofile.is_dispatcher:
            self.request.session.set_expiry(14 * 24 * 60 * 60)

        return result


# logout

class LogoutView(auth_views.LogoutView):
    next_page = '/'


# Groups

class GroupAdminListView(ListView):
    model = Group
    template_name = 'login/group_list.html'
    ordering = ['-groupprofile__priority', 'name']


class GroupAdminDetailView(DetailView):
    model = Group
    template_name = 'login/group_detail.html'
    fields = ['name']

    def get_context_data(self, **kwargs):

        # call super to retrieve object
        context = super().get_context_data(**kwargs)

        # retrieve permissions and add to context
        context['ambulance_list'] = self.object.groupambulancepermission_set.all()
        context['hospital_list'] = self.object.grouphospitalpermission_set.all()

        # retrieve users and add to context
        context['user_list'] = self.object.user_set.all()

        return context


class GroupProfileAdminInline(InlineFormSet):
    model = GroupProfile
    form_class = GroupProfileAdminForm
    factory_kwargs = {
        'min_num': 1,
        'max_num': 1,
        'extra': 0,
        'can_delete': False
    }


class GroupAmbulancePermissionAdminInline(InlineFormSet):
    model = GroupAmbulancePermission
    form_class = GroupAmbulancePermissionAdminForm
    factory_kwargs = {
        'extra': 1
    }


class GroupHospitalPermissionAdminInline(InlineFormSet):
    model = GroupHospitalPermission
    form_class = GroupHospitalPermissionAdminForm
    factory_kwargs = {
        'extra': 1
    }


class GroupAdminCreateView(SuccessMessageMixin,
                           CreateView):
    model = Group
    fields = ['name']
    template_name = 'login/group_create.html'

    def get_success_message(self, cleaned_data):
        return "Successfully created group '{}'".format(cleaned_data['name'])

    def get_success_url(self):
        return self.object.groupprofile.get_absolute_url()


class GroupAdminUpdateView(SuccessMessageWithInlinesMixin,
                           UpdateWithInlinesView):
    model = Group
    template_name = 'login/group_form.html'
    form_class = GroupAdminUpdateForm
    inlines = [GroupProfileAdminInline,
               GroupAmbulancePermissionAdminInline,
               GroupHospitalPermissionAdminInline]

    def get_success_message(self, cleaned_data):
        return "Successfully updated group '{}'".format(self.object.name)

    def get_success_url(self):
        return self.object.groupprofile.get_absolute_url()


# Users

class UserProfileAdminInline(InlineFormSet):
    model = UserProfile
    form_class = UserProfileAdminForm
    factory_kwargs = {
        'min_num': 1,
        'max_num': 1,
        'extra': 0,
        'can_delete': False
    }


class UserAdminListView(ListView):
    model = User
    template_name = 'login/user_list.html'
    ordering = ['username']


class UserAdminDetailView(DetailView):
    model = User
    template_name = 'login/user_detail.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active']

    def get_context_data(self, **kwargs):

        # call super to retrieve object
        context = super().get_context_data(**kwargs)

        # retrieve permissions and add to context
        context['ambulance_list'] = self.object.userambulancepermission_set.all()
        context['hospital_list'] = self.object.userhospitalpermission_set.all()

        # retrieve groups and add to context
        context['group_list'] = self.object.groups.all()

        return context


class UserAmbulancePermissionAdminInline(InlineFormSet):
    model = UserAmbulancePermission
    form_class = UserAmbulancePermissionAdminForm
    factory_kwargs = {
        'extra': 1
    }


class UserHospitalPermissionAdminInline(InlineFormSet):
    model = UserHospitalPermission
    form_class = UserHospitalPermissionAdminForm
    factory_kwargs = {
        'extra': 1
    }


class UserAdminCreateView(SuccessMessageWithInlinesMixin,
                          CreateWithInlinesView):
    model = User
    template_name = 'login/user_form.html'
    form_class = UserAdminCreateForm
    inlines = [UserProfileAdminInline,
               UserAmbulancePermissionAdminInline,
               UserHospitalPermissionAdminInline]

    def forms_valid(self, form, inlines):

        # process form
        response = self.form_valid(form)

        # update userprofile without creating
        # userprofile is created by a signal
        # not sure if the signal is called synchronously with the call to save()
        # if not, this could be subject to a concurrency issue
        # the following post claims they are not asynchronous
        # https://stackoverflow.com/questions/11899088/is-django-post-save-signal-asynchronous
        userprofile_form = inlines[0][0]
        userprofile_form.cleaned_data.pop('id', None)
        UserProfile.objects.filter(user=form.instance).update(**userprofile_form.cleaned_data)

        # process other inlines
        for formset in inlines[1:]:
            formset.save()

        return response

    def get_success_message(self, cleaned_data):
        return "Successfully updated user '{}'".format(self.object.username)

    def get_success_url(self):
        return self.object.userprofile.get_absolute_url()


class UserAdminUpdateView(SuccessMessageWithInlinesMixin,
                          UpdateWithInlinesView):
    model = User
    template_name = 'login/user_form.html'
    form_class = UserAdminUpdateForm
    inlines = [UserProfileAdminInline,
               UserAmbulancePermissionAdminInline,
               UserHospitalPermissionAdminInline]

    def get_success_message(self, cleaned_data):
        return "Successfully updated user '{}'".format(self.object.username)

    def get_success_url(self):
        return self.object.userprofile.get_absolute_url()


# Clients

class ClientListView(ListView):
    model = Client
    queryset = Client.objects.filter(status=ClientStatus.O.name)
    ordering = ['-status', '-updated_on']

    def get_context_data(self, **kwargs):

        # add paginated offline clients to context

        # call supper
        context = super().get_context_data(**kwargs)

        # query
        not_online_query = Client.objects.exclude(status=ClientStatus.O.name).order_by('-updated_on')

        # get current page
        page = self.request.GET.get('page', 1)
        page_size = self.request.GET.get('page_size', 25)
        page_sizes = [25, 50, 100]

        # paginate
        paginator = Paginator(not_online_query, page_size)
        try:
            not_online = paginator.page(page)
        except PageNotAnInteger:
            not_online = paginator.page(1)
        except EmptyPage:
            not_online = paginator.page(paginator.num_pages)

        context['not_online'] = not_online
        context['page_links'] = get_page_links(self.request, not_online)
        context['page_size_links'] = get_page_size_links(self.request, not_online, page_sizes)
        context['page_size'] = int(page_size)

        return context


class ClientDetailView(DetailView):
    model = Client

    def get_context_data(self, **kwargs):

        # call super to retrieve object
        context = super().get_context_data(**kwargs)

        # retrieve log
        context['clientlog_list'] = self.object.clientlog_set.all().order_by('-updated_on')

        return context


# Restart

class RestartView(FormView):
    form_class = RestartForm
    template_name = 'modal.html'

    def get_success_url(self):
        return self.request.GET.get('next', '/')

    def get_context_data(self, **kwargs):

        # call super to retrieve object
        context = super().get_context_data(**kwargs)

        # customize modal form
        context['title'] = 'EMSTrack Reinitialization'
        context['foreword'] = '<p>This command will invalidate the permission cache and reinitialize ' + \
                              'all settings.</p>' + \
                              '<p>This is not usually necessary but can be helpful when modifying users, ' + \
                              'groups and permissions.</p>'
        context['afterword'] = '<p>Click <strong>OK</strong> if you would like to proceed or ' + \
                               '<strong>Cancel</strong> otherwise.</p>'
        context['next'] = self.get_success_url()

        return context

    def form_valid(self, form):

        try:

            # invalidate permission cache
            mqtt_cache_clear()

            # add message
            messages.info(self.request, 'Successfully reinitialized system.')

            # call super form_valid
            return super().form_valid(form)

        except Exception as error:

            # add error to form
            form.add_error(None, error)

            # call super form_invalid
            return super().form_invalid(form);


# MQTT login views

class MQTTLoginView(CsrfExemptMixin,
                    FormView):
    """
    Authenticate user without logging in. 
    It is meant to be used for MQTT authentication only.
    """

    template_name = 'login/mqtt_login.html'
    form_class = MQTTAuthenticationForm

    def form_invalid(self, form):
        return HttpResponseForbidden()

    def form_valid(self, form):
        return HttpResponse('OK')


class MQTTSuperuserView(CsrfExemptMixin,
                        View):
    """
    Verify if user is superuser.
    """

    http_method_names = ['post', 'head', 'options']

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA
        try:
            user = User.objects.get(username=data.get('username'),
                                    is_active=True)
            if user.is_superuser or user.is_staff:
                return HttpResponse('OK')

        except User.DoesNotExist:
            pass

        return HttpResponseForbidden()


class MQTTAclView(CsrfExemptMixin,
                  View):
    """
    Verify MQTT ACL permissions.
    """

    http_method_names = ['post', 'head', 'options']

    def post(self, request, *args, **kwargs):
        data = {}
        if hasattr(request, 'POST'):
            data = request.POST
        elif hasattr(request, 'DATA'):
            data = request.DATA
        allow = False

        # Check permissions
        username = data.get('username')
        clientid = data.get('clientid')
        acc = int(data.get('acc'))  # 1 == sub, 2 == pub

        # get topic and remove first '/'
        topic = data.get('topic').split('/')
        if len(topic) > 0 and topic[0] == '':
            del topic[0]

        try:

            # get user
            user = User.objects.get(username=username,
                                    is_active=True)

            if acc == 1:

                # permission to subscribe:

                # is user admin?
                if user.is_staff:
                    return HttpResponse('OK')

                #  - settings
                if (len(topic) == 1 and
                        topic[0] == 'settings'):

                    return HttpResponse('OK')

                #  - user/{username}/error
                #  - user/{username}/profile
                elif (len(topic) == 3 and
                      topic[0] == 'user' and
                      topic[1] == user.username):

                    if (topic[2] == 'profile' or
                            topic[2] == 'error'):
                        return HttpResponse('OK')

                #  - hospital/{hospital-id}/data
                elif (len(topic) == 3 and
                      topic[0] == 'hospital' and
                      topic[2] == 'data'):

                    # get hospital id
                    hospital_id = int(topic[1])

                    # is user authorized?
                    try:

                        # perm = user.profile.hospitals.get(hospital=hospital_id)
                        can_read = get_permissions(user).check_can_read(hospital=hospital_id)

                        if (can_read):
                            return HttpResponse('OK')

                    except ObjectDoesNotExist:
                        pass

                #  - equipment/{equipment-holder-id}/metadata
                #  - equipment/{equipment-holder-id}/item/+/data
                elif (len(topic) >= 3 and
                      topic[0] == 'equipment'):

                    # get equipmentholder_id
                    equipmentholder_id = int(topic[1])
                    # logger.debug('equipmentholder_id = {}'.format(equipmentholder_id))

                    # is user authorized?
                    try:

                        # perm = user.profile.hospitals.get(hospital=hospital_id)
                        can_read = get_permissions(user).check_can_read(equipment=equipmentholder_id)
                        # logger.debug('can read? = {}'.format(can_read))

                        # can read?
                        if (can_read and
                                ((len(topic) == 3 and topic[2] == 'metadata') or
                                 (len(topic) == 5 and topic[2] == 'item' and topic[4] == 'data'))):
                            return HttpResponse('OK')

                    except ObjectDoesNotExist:
                        # logger.debug('ObjectDoesNotExist exception')
                        pass

                #  - ambulance/{ambulance-id}/data
                #  - ambulance/{ambulance-id}/call/{call-id}/status
                elif (len(topic) >= 3 and
                      topic[0] == 'ambulance'):

                    # get ambulance_id
                    ambulance_id = int(topic[1])

                    # is user authorized?
                    try:

                        # perm = user.profile.ambulances.get(ambulance=ambulance_id)
                        can_read = get_permissions(user).check_can_read(ambulance=ambulance_id)

                        if (can_read and
                                ((len(topic) == 3 and topic[2] == 'data') or
                                 (len(topic) == 5 and topic[2] == 'call' and topic[4] == 'status'))):
                            return HttpResponse('OK')

                    except ObjectDoesNotExist:
                        pass

                #  - call/{call-id}/data
                elif (len(topic) == 3 and
                      topic[0] == 'call' and
                      topic[2] == 'data'):

                    # get ambulance_id
                    call_id = int(topic[1])

                    # is user authorized?
                    try:

                        # retrieve call
                        call = Call.objects.get(id=call_id)

                        # can read ambulance in call?
                        for ambulancecall in call.ambulancecall_set.all():

                            can_read = get_permissions(user).check_can_read(ambulance=ambulancecall.ambulance_id)
                            if (can_read):
                                return HttpResponse('OK')

                    except ObjectDoesNotExist:
                        pass

            elif acc == 2:

                # permission to publish:

                #  - message
                if (len(topic) == 1 and
                        topic[0] == 'message' and
                        user.is_superuser):

                    return HttpResponse('OK')

                #  - user/{username}/client/{client-id}/#
                elif (len(topic) >= 5 and
                        topic[0] == 'user' and
                        topic[1] == user.username and
                        topic[2] == 'client' and
                        topic[3] == clientid):

                    #  - user/{username}/client/{client-id}/error
                    #  - user/{username}/client/{client-id}/status
                    if (len(topic) == 5 and
                            (topic[4] == 'error' or topic[4] == 'status')):

                        return HttpResponse('OK')

                    #  - user/{username}/client/{client-id}/ambulance/{ambulance-id}/data
                    #  - user/{username}/client/{client-id}/ambulance/{ambulance-id}/call/{call-id}/status
                    #  - user/{username}/client/{client-id}/ambulance/{ambulance-id}/call/{call-id}/waypoint/{waypoint_id}/data
                    elif (topic[4] == 'ambulance' and
                          ((len(topic) == 7 and topic[6] == 'data') or
                           (len(topic) == 9 and topic[6] == 'call' and topic[8] == 'status') or
                           (len(topic) == 11 and
                            topic[6] == 'call' and topic[8] == 'waypoint' and topic[10] == 'data'))):

                        # get ambulance_id
                        ambulance_id = int(topic[5])

                        # is user authorized?
                        try:

                            # perm = user.profile.ambulances.get(ambulance=ambulance_id)
                            can_write = get_permissions(user).check_can_write(ambulance=ambulance_id)

                            if can_write:
                                return HttpResponse('OK')

                        except ObjectDoesNotExist:
                            pass

                    #  - user/{username}/client/{client-id}/hospital/{hospital-id}/data
                    elif (topic[4] == 'hospital' and
                          len(topic) == 7 and topic[6] == 'data'):

                        # get hospital_id
                        hospital_id = int(topic[5])

                        # is user authorized?
                        try:

                            # perm = user.profile.hospitals.get(hospital=hospital_id)
                            can_write = get_permissions(user).check_can_write(hospital=hospital_id)

                            if can_write:
                                return HttpResponse('OK')

                        except ObjectDoesNotExist:
                            pass

                    #  - user/{username}/client/{client-id}/equipment/{equipment-holder-id}/item/+/data
                    elif (topic[4] == 'equipment' and
                          len(topic) == 9 and topic[6] == 'item' and topic[8] == 'data'):

                        # get equipmentholder_id
                        equipmentholder_id = int(topic[1])

                        # is user authorized?
                        try:

                            # perm = user.profile.hospitals.get(hospital=hospital_id)
                            can_write = get_permissions(user).check_can_write(equipment=equipmentholder_id)

                            if can_write:
                                return HttpResponse('OK')

                        except ObjectDoesNotExist:
                            pass

        except User.DoesNotExist:
            pass

        return HttpResponseForbidden()


class PasswordView(APIView):
    """
    Retrieve password to use with MQTT.
    """

    @staticmethod
    def generate_password(size=20,
                          chars=(string.ascii_letters +
                                 string.digits +
                                 string.punctuation)):
        return ''.join(random.choice(chars) for _ in range(size))

    def get(self, request, user__username=None):
        """
        Generate temporary password if one does not exist or is invalid.
        Stores password in the database and returns a hash. Users in 
        possesion of this hash will be able to login through MQTT. 
        Passwords are valid for 120 seconds. 
        A new hash is however returned every time.
        """

        # retrieve current user
        user = request.user

        # make sure user and username are the same
        if user.username != user__username:
            raise PermissionDenied()

        try:

            # Retrieve current password
            pwd = TemporaryPassword.objects.get(user=user.id)
            password = pwd.password
            valid_until = pwd.created_on + timedelta(seconds=120)

            # Invalidate password if it is expired
            if timezone.now() > valid_until:
                password = None

        except ObjectDoesNotExist:

            pwd = None
            password = None

        if password is None:

            # Generate password
            password = self.generate_password()

            if pwd is None:

                # create password
                pwd = TemporaryPassword(user=user,
                                        password=password)

            else:

                # update password
                pwd.password = password

            # save password
            pwd.save()

        # Return password hash
        password_hash = make_password(password=password)

        return Response(password_hash)


class SettingsView(APIView):
    """
    Retrieve current settings and options.
    """

    @staticmethod
    def get_settings():

        # from ambulance/models.py
        ambulance_status = {m.name: m.value for m in AmbulanceStatus}
        ambulance_status_order = [m.name for m in AmbulanceStatusOrder]
        ambulance_capability = {m.name: m.value for m in AmbulanceCapability}
        ambulance_capability_order = [m.name for m in AmbulanceCapabilityOrder]
        call_priority = {m.name: m.value for m in CallPriority}
        call_priority_order = [m.name for m in CallPriorityOrder]
        call_status = {m.name: m.value for m in CallStatus}
        call_status_order = [m.name for m in CallStatusOrder]
        ambulancecall_status = {m.name: m.value for m in AmbulanceCallStatus}
        location_type = {m.name: m.value for m in LocationType}
        location_type_order = [m.name for m in LocationTypeOrder]
        waypoint_status = {m.name: m.value for m in WaypointStatus}

        # from equipment/models.py
        equipment_type = {m.name: m.value for m in EquipmentType}
        equipment_type_defaults = {k: v for (k,v) in EquipmentTypeDefaults.items()}

        # assemble all settings
        all_settings = {'ambulance_status': ambulance_status,
                        'ambulance_status_order': ambulance_status_order,
                        'ambulance_capability': ambulance_capability,
                        'ambulance_capability_order': ambulance_capability_order,
                        'call_priority': call_priority,
                        'call_priority_order': call_priority_order,
                        'call_status': call_status,
                        'call_status_order': call_status_order,
                        'ambulancecall_status': ambulancecall_status,
                        'location_type': location_type,
                        'location_type_order': location_type_order,
                        'waypoint_status': waypoint_status,
                        'equipment_type': equipment_type,
                        'equipment_type_defaults': equipment_type_defaults,
                        'defaults': defaults.copy()}

        # serialize defaults.location
        all_settings['defaults']['location'] = PointField().to_representation(defaults['location'])

        return all_settings

    def get(self, request, user__username=None):
        """
        Retrieve current settings and options.
        """

        return Response(self.get_settings())


class VersionView(APIView):
    """
    Retrieve current version.
    """

    @staticmethod
    def get_version():

        # assemble all settings
        version = {'current': CURRENT_VERSION,
                   'minimum': MINIMUM_VERSION}

        return version

    def get(self, request, user__username=None):
        """
        Retrieve current version.
        """

        return Response(self.get_version())


class ClientLogoutView(LoginRequiredMixin,
                       SuccessMessageMixin,
                       UpdatedByMixin,
                       BaseDetailView):
    model = Client

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get(self, request, *args, **kwargs):

        # Make sure user is super or staff
        user = request.user
        if not (user.is_superuser or user.is_staff):
            return HttpResponseForbidden()

        # get client
        self.object = self.get_object()
        client = self.object

        # remove ambulance
        client.ambulance = None
        client.save()

        return redirect(client)
