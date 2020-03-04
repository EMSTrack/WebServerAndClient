from django.core.exceptions import PermissionDenied

from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from emstrack.mixins import UpdateModelUpdateByMixin, BasePermissionMixin
from equipment.models import EquipmentItem, EquipmentHolder, Equipment
from equipment.serializers import EquipmentItemSerializer, EquipmentSerializer
from hospital.viewsets import logger
from login.permissions import get_permissions


class EquipmentItemViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           UpdateModelUpdateByMixin,
                           viewsets.GenericViewSet):
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

    # make sure both fields are looked up
    def get_queryset(self,equipmentholder_id=None):

        # retrieve user
        user = self.request.user

        # return nothing if anonymous
        if user.is_anonymous:
            raise PermissionDenied()
        
        # retrieve id
        if equipmentholder_id is None:
            equipmentholder_id = int(self.kwargs['equipmentholder_id'])
        logger.debug('kwargs = {}'.format(self.kwargs))

        try:
            
            # retrieve equipmentholder
            equipmentholder = EquipmentHolder.objects.get(id=equipmentholder_id)

            # read or write?
            if self.request.method == 'GET':
                is_write = False
            elif (self.request.method == 'PUT' or
                  self.request.method == 'PATCH' or
                  self.request.method == 'DELETE'):
                is_write = True

            # is hospital?
            if equipmentholder.is_hospital():

                # check permission (and also existence)
                if is_write:
                    if not get_permissions(user).check_can_write(hospital=equipmentholder.hospital.id):
                        raise PermissionDenied()
                else:
                    if not get_permissions(user).check_can_read(hospital=equipmentholder.hospital.id):
                        raise PermissionDenied()

            # is ambulance?
            elif equipmentholder.is_ambulance():

                # check permission (and also existence)
                if is_write:
                    if not get_permissions(user).check_can_write(ambulance=equipmentholder.ambulance.id):
                        raise PermissionDenied()
                else:
                    if not get_permissions(user).check_can_read(ambulance=equipmentholder.ambulance.id):
                        raise PermissionDenied()

            else:
                raise PermissionDenied()

        except EquipmentHolder.DoesNotExist as e:
            raise PermissionDenied()

        # build queryset
        filter = {'equipmentholder_id': 2}
        return self.queryset.filter(**filter)



class EquipmentViewSet(BasePermissionMixin,
                       viewsets.GenericViewSet):
    """
    API endpoint for manipulating equipment.

    metadata:
    Retrieve equipment metadata.
    """

    profile_field = 'equipments'
    filter_field = 'id'
    queryset = EquipmentHolder.objects.all()

    @action(detail=True)
    def metadata(self, request, pk=None, **kwargs):
        """
        Retrive equipment metadata.
        """

        equipmentholder = self.get_object()
        equipment_list = equipmentholder.equipmentitem_set.values('equipment')
        equipment = Equipment.objects.filter(id__in=equipment_list)
        serializer = EquipmentSerializer(equipment, many=True)
        return Response(serializer.data)
