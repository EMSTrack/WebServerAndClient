from django.http import Http404
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.exceptions import APIException, NotFound
from rest_framework.status import HTTP_400_BAD_REQUEST

from ambulance.permissions import CallPermissionMixin
from emstrack.mixins import BasePermissionMixin, \
    CreateModelUpdateByMixin, UpdateModelUpdateByMixin
from login.permissions import IsCreateByAdminOrSuperOrDispatcher, IsAdminOrSuperOrDispatcher

from .models import Location, Ambulance, LocationType, Call, AmbulanceUpdate, AmbulanceCall, AmbulanceCallHistory, \
    AmbulanceCallStatus, CallStatus, CallPriorityClassification, CallPriorityCode, CallRadioCode

from .serializers import LocationSerializer, AmbulanceSerializer, AmbulanceUpdateSerializer, CallSerializer, \
    CallPriorityCodeSerializer, CallPriorityClassificationSerializer, CallRadioCodeSerializer

from equipment.models import EquipmentItem
from equipment.serializers import EquipmentItemSerializer
from equipment.viewsets import EquipmentViewSet
import logging
logger = logging.getLogger(__name__)


# Django REST Framework Viewsets
class AmbulanceEquipmentItemViewSet(EquipmentItemViewSet):
    """
    API endpoint for manipulating ambulance equipment.

    list:
    Retrieve list of equipment.

    retrieve:
    Retrieve an existing equipment instance.

    update:
    Update existing equipment instance.

    partial_update:
    Partially update existing equipment instance.
    """
    queryset = EquipmentItem.objects.all()

    serializer_class = EquipmentItemSerializer
    lookup_field = 'equipment_id'
    def get_queryset(self):
        
        ambulance_id = int(self.kwargs['ambulance_id'])
        ambulance = Ambulance.objects.get(id=ambulance_id)
        equipmentholder_id = ambulance.equipmentholder.id
        return super().get_queryset(equipmentholder_id)
        

class AmbulancePageNumberPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    # page_size = 25
    max_page_size = 1000


class AmbulanceLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 1000


# Ambulance viewset

class AmbulanceViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       CreateModelUpdateByMixin,
                       UpdateModelUpdateByMixin,
                       BasePermissionMixin,
                       viewsets.GenericViewSet):
    """
    API endpoint for manipulating ambulances.

    list:
    Retrieve list of ambulances.

    retrieve:
    Retrieve an existing ambulance instance.

    create:
    Create new ambulance instance.
    
    update:
    Update existing ambulance instance.

    partial_update:
    Partially update existing ambulance instance.
    """

    filter_field = 'id'
    profile_field = 'ambulances'
    queryset = Ambulance.objects.all()

    serializer_class = AmbulanceSerializer

    @action(detail=True, methods=['get'])
    def calls(self, request, pk=None, **kwargs):
        """Retrieve active calls for ambulance instance."""
        calls = Call.objects.filter(ambulancecall__ambulance_id=pk).exclude(status=CallStatus.E.name)

        serializer = CallSerializer(calls, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'], pagination_class=AmbulancePageNumberPagination)
    def updates(self, request, pk=None, **kwargs):
        """Bulk retrieve/update ambulance updates."""
        if request.method == 'GET':
            # list updates
            return self.updates_get(request, pk, **kwargs)

        elif request.method == 'POST':
            # put updates
            return self.updates_put(request, pk, updated_by=self.request.user, **kwargs)

    # Filter out the working time of ambulance and extract the unavailable time range for ambulance
    @staticmethod
    def extract_unavailable_zone(ambulance_history):

        unavailable_zone = [None]
        accepted = False

        for h in ambulance_history:

            # Started timestamp
            if accepted is False and h.status == AmbulanceCallStatus.A.name:
                unavailable_zone.append(h.updated_on)
                accepted = True

            # If we already seen accepted status, seeing another kind of status
            elif accepted is True and h.status != AmbulanceCallStatus.A.name:
                unavailable_zone.append(h.updated_on)
                accepted = False

        # If the last status is not accepted, we should put a None to ensure pair
        if accepted is False:
            unavailable_zone.append(None)

        return unavailable_zone

    # Filter out the working time of ambulance and extract the available time range for ambulance
    @staticmethod
    def extract_available_zone(ambulance_history):

        available_zone = []
        accepted = False

        for h in ambulance_history:

            # logger.debug('status = %s, updated_on = %s', h.status, h.updated_on)

            # Started timestamp
            if accepted is False and h.status == AmbulanceCallStatus.A.name:
                available_zone.append(h.updated_on)
                accepted = True

            # If we already seen accepted status, seeing another kind of status
            elif accepted is True and h.status != AmbulanceCallStatus.A.name:
                available_zone.append(h.updated_on)
                accepted = False

        # If the last status is not accepted, we should put a None to ensure pair
        if accepted is True:
            available_zone.append(None)

        return available_zone

    def updates_get(self, request, pk=None, **kwargs):
        """
        Retrieve and paginate ambulance updates.
        Use ?page=10&page_size=100 to control pagination.
        Use ?call_id=x to retrieve updates to call x.
        """

        # retrieve updates
        ambulance = self.get_object()
        ambulance_updates = ambulance.ambulanceupdate_set.all()
        # logger.debug(ambulance_updates)

        # retrieve only call updates
        call_id = self.request.query_params.get('call_id', None)
        if call_id is not None:
            try:

                # retrieve call
                call = Call.objects.get(id=call_id)

                # retrieve ambulance_call
                ambulance_call = AmbulanceCall.objects.get(ambulance=ambulance, call=call)

            except (Call.DoesNotExist, Ambulance.objects.DoesNotExist) as e:
                raise Http404("Call with id '{}' does not exist.".format(call_id))

            ambulance_history = AmbulanceCallHistory.objects\
                .filter(ambulance_call=ambulance_call)\
                .order_by('updated_on')
            # logger.debug(ambulance_history)

            if ambulance_history:

                # If there is available history, filter call based on active intervals

                # parse active times
                available_times = self.extract_available_zone(ambulance_history)
                # logger.debug(available_times)
                # for entry in ambulance_updates:
                #     logger.debug(entry.timestamp)

                if available_times:
                    # create filter to include only active times
                    ranges = []
                    for (t1, t2) in zip(*[iter(available_times)] * 2):
                        if t2 is None:
                            ranges.append(ambulance_updates.filter(timestamp__gte=t1))
                        else:
                            ranges.append(ambulance_updates.filter(timestamp__range=(t1, t2)))

                    # calculate union of the active intervals
                    if len(ranges) == 1:
                        ambulance_updates = ranges[0]
                    elif len(ranges) > 1:
                        ambulance_updates = ranges[0].union(*ranges[1:])
                    # logger.debug(ambulance_updates)

                else:
                    # no active time yet, return nothing!
                    ambulance_updates = AmbulanceUpdate.objects.none()

            else:

                # If no history is available, go for compatibility

                # if the call is ended
                if call.ended_at is not None:
                    ambulance_updates = ambulance_updates.filter(timestamp__range=(call.started_at, call.ended_at))

                # iff the call is still active
                elif call.started_at is not None:
                    ambulance_updates = ambulance_updates.filter(timestamp__gte=call.started_at)

                # call hasn't started yet, return none
                else:
                    ambulance_updates = AmbulanceUpdate.objects.none()

            # order records in ascending order
            ambulance_updates = ambulance_updates.order_by('timestamp')

        else:

            # order records in descending order
            ambulance_updates = ambulance_updates.order_by('-timestamp')

        # for entry in ambulance_updates:
        #     logger.debug(entry.timestamp)

        # paginate
        page = self.paginate_queryset(ambulance_updates)

        if page is not None:
            serializer = AmbulanceUpdateSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # return all if not paginated
        serializer = AmbulanceUpdateSerializer(ambulance_updates, many=True)
        return Response(serializer.data)

    def updates_put(self, request, pk=None, **kwargs):
        """
        Bulk ambulance updates.
        """

        # retrieve ambulance
        ambulance = self.get_object()

        # retrieve user
        updated_by = kwargs.pop('updated_by')

        # update all serializers
        serializer = AmbulanceUpdateSerializer(data=request.data,
                                               many=True)
        if serializer.is_valid():
            serializer.save(ambulance=ambulance, updated_by=updated_by)
            return Response(serializer.data)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


# Location viewset

class LocationViewSet(mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    """
    API endpoint for manipulating locations.

    list:
    Retrieve list of locations.
    """
    queryset = Location.objects.exclude(type=LocationType.h.name).exclude(type=LocationType.w.name)
    serializer_class = LocationSerializer


class LocationTypeViewSet(mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    API endpoint for manipulating locations.

    list:
    Retrieve list of locations by type.
    """
    serializer_class = LocationSerializer

    def get_queryset(self):
        try:
            location_type_name = self.kwargs['type']
            # location_type_name = LocationType(location_type).name
        except ValueError:
            raise APIException("Invalid location type '{}'".format(location_type_name))

        return Location.objects.filter(type=location_type_name)


# Call ViewSet

class CallViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  UpdateModelUpdateByMixin,
                  CreateModelUpdateByMixin,
                  CallPermissionMixin,
                  viewsets.GenericViewSet):
    """
    API endpoint for manipulating Calls.

    list:
    Retrieve list of calls.

    create:
    Create new call instance.

    retrieve:
    Retrieve an existing call instance.

    abort:
    Abort an existing call instance.

    update:
    Full call instance updates are not supported.

    partial_update:
    Partially update existing call instance.
    """

    permission_classes = (IsAuthenticated,
                          IsCreateByAdminOrSuperOrDispatcher)

    filter_field = 'ambulancecall__ambulance_id'
    profile_field = 'ambulances'
    queryset = Call.objects.all()

    serializer_class = CallSerializer

    def get_queryset(self):

        # grab all objects from super, enforces permissions
        queryset = super().get_queryset()

        status = self.request.query_params.get('status', None)
        exclude = self.request.query_params.get('exclude', CallStatus.E.name)

        # filter by status
        if status is not None:
            queryset = queryset.filter(status=status)
        elif exclude is not None:
            queryset = queryset.exclude(status=exclude)

        return queryset

    @action(detail=True, methods=['get'], permission_classes=[IsAdminOrSuperOrDispatcher])
    def abort(self, request, pk=None, **kwargs):
        """Abort call."""

        # get call object
        call = self.get_object()

        # abort call
        call.abort()

        # serialize and return
        serializer = CallSerializer(call)
        return Response(serializer.data)


# CallPriorityViewSet

class CallPriorityViewSet(mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    API endpoint for manipulating priority codes.

    list:
    Retrieve list of priority codes.
    """

    queryset = CallPriorityCode.objects.all()
    serializer_class = CallPriorityCodeSerializer

    @action(detail=False, methods=['get'])
    def classification(self, request, **kwargs):
        """Retrieve priority classification labels."""
        classification = CallPriorityClassification.objects.all()

        serializer = CallPriorityClassificationSerializer(classification, many=True)
        return Response(serializer.data)


# CallRadioViewSet

class CallRadioViewSet(mixins.ListModelMixin,
                       viewsets.GenericViewSet):
    """
    API endpoint for manipulating radio codes.

    list:
    Retrieve list of radio codes.
    """

    queryset = CallRadioCode.objects.all()
    serializer_class = CallRadioCodeSerializer
