import logging

from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from emstrack.mixins import BasePermissionMixin, \
    CreateModelUpdateByMixin, UpdateModelUpdateByMixin

from .models import Hospital
from equipment.models import Equipment

from .serializers import HospitalSerializer
from equipment.serializers import EquipmentSerializer

logger = logging.getLogger(__name__)


# Django REST Framework Viewsets


# Hospital viewset

class HospitalViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      CreateModelUpdateByMixin,
                      UpdateModelUpdateByMixin,
                      BasePermissionMixin,
                      viewsets.GenericViewSet):
    """
    API endpoint for manipulating hospitals.

    list:
    Retrieve list of hospitals.

    retrieve:
    Retrieve an existing hospital instance.

    create:
    Create new hospital instance.
    
    update:
    Update existing hospital instance.

    partial_update:
    Partially update existing hospital instance.
    """

    filter_field = 'id'
    profile_field = 'hospitals'
    queryset = Hospital.objects.all()

    serializer_class = HospitalSerializer