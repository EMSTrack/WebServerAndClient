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

from equipment.viewsets import EquipmentItemViewSet
from equipment.serializers import EquipmentItemSerializer
from equipment.models import EquipmentItem
from login.permissions import get_permissions
from django.core.exceptions import PermissionDenied


logger = logging.getLogger(__name__)


# Django REST Framework Viewsets
class HospitalEquipmentItemViewSet(EquipmentItemViewSet):
    """
    API endpoint for manipulating equipment.

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
        user = self.request.user
        hospital_id = int(self.kwargs['hospital_id'])
        hostpital = Hospital.objects.get(id=hospital_id)
        equipmentholder = hostpital.equipmentholder
        equipmentholder_id = equipmentholder.id
        if self.request.method == 'GET':
            is_write = False
        elif (self.request.method == 'PUT' or
                self.request.method == 'PATCH' or
                self.request.method == 'DELETE'):
            is_write = True

                # check permission (and also existence)
        if is_write:
            if not get_permissions(user).check_can_write(hospital=equipmentholder.hospital.id):
                raise PermissionDenied()
        else:
            if not get_permissions(user).check_can_read(hospital=equipmentholder.hospital.id):
                raise PermissionDenied()
        
        # build queryset
        filter = {'equipmentholder_id': equipmentholder_id}
        return self.queryset.filter(**filter)



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