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

from equipment.viewsets import EquipmentItemViewSet
from equipment.models import EquipmentItem
from equipment.serializers import EquipmentItemSerializer
    

# Django REST Framework Viewsets
class HospitalEquipmentItemViewSet(EquipmentItemViewSet):
    """
    API endpoint for manipulating hospital equipment.

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
        
        hospital_id = int(self.kwargs['hospital_id'])
        hospital = Hospital.objects.get(id=hospital_id)
        equipmentholder_id = hospital.equipmentholder.id
        return super().get_queryset(equipmentholder_id)


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
