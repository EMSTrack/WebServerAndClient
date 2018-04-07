import logging
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction

from rest_framework import serializers
from drf_extra_fields.geo_fields import PointField

from login.models import Client
from login.permissions import get_permissions
from .models import Ambulance, AmbulanceUpdate, Call, Location, AmbulanceCallTime, Patient
from emstrack.latlon import calculate_orientation

logger = logging.getLogger(__name__)


# Ambulance serializers

class AmbulanceSerializer(serializers.ModelSerializer):

    location_client_id = serializers.CharField(source='location_client.client_id',
                                               required=False, allow_blank=True, allow_null=True)
    location = PointField(required=False)
    
    class Meta:
        model = Ambulance
        fields = ['id', 'identifier',
                  'capability', 'status',
                  'orientation', 'location',
                  'timestamp', 'location_client_id',
                  'comment', 'updated_by', 'updated_on']
        read_only_fields = ('updated_by',)

    def validate_location_client_id(self, value):

        if value:
            try:
                Client.objects.get(client_id=value)
            except Client.DoesNotExist:
                raise serializers.ValidationError("Client '{}' does not exist".format(value))

        return value

    def validate(self, data):

        # timestamp must be defined together with either comment, status or location
        if 'timestamp' in data and not ('comment' in data or 'location' in data or 'status' in data):
            raise serializers.ValidationError('timestamp can only be set when either comment, location, ' +
                                              'or status are modified')

        return data

    def create(self, validated_data):

        # get current user
        user = validated_data['updated_by']

        # check credentials
        # only super can create
        if not user.is_superuser:
            raise PermissionDenied()
    
        return super().create(validated_data)
    
    def update(self, instance, validated_data):

        # get current user
        user = validated_data['updated_by']

        # check credentials
        if not user.is_superuser:

            # serializer.instance will always exist!
            # if not user.profile.ambulances.filter(can_write=True,
            #                                      ambulance=instance.id):
            if not get_permissions(user).check_can_write(ambulance=instance.id):
                raise PermissionDenied()

        # update location_client
        # stored in validated_data as {'location_client': {'client_id': client_id}}
        if 'location_client' in validated_data:

            client_id = validated_data.pop('location_client')['client_id']

            location_client = None
            if client_id:
                location_client = Client.objects.get(client_id=client_id)

            if instance.location_client is None or location_client is None:

                # fine, clear or update location client
                validated_data['location_client'] = location_client

        logger.debug('validated_data = {}'.format(validated_data))

        return super().update(instance, validated_data)


class AmbulanceUpdateListSerializer(serializers.ListSerializer):

    def create(self, validated_data):

        def process_update(update, current):

            # calculate orientation?
            if ('orientation' not in update and
                    'location' in update and
                    update['location'] != current['location']):

                    current['orientation'] = calculate_orientation(current['location'], update['location'])
                    logger.debug('< {} - {} = {}'.format(current['location'],
                                                         update['location'],
                                                         current['orientation']))

            # clear timestamp
            current.pop('timestamp', None)

            # update data
            current.update(**update)

            return current

        logger.debug('validated_data = {}'.format(validated_data))

        # process updates inside a transaction
        try:

            with transaction.atomic():

                # loop through updates
                instances = []
                n = len(validated_data)

                # short return
                if n == 0:
                    return

                # get ambulance and create template from first update
                # all ambulances are the same in a bulk update
                ambulance = validated_data[0].get('ambulance')
                data = {k: getattr(ambulance, k) for k in ('status', 'orientation', 'location', 'comment')}

                # loop through
                for k in range(0, n-1):

                    # process update
                    retdata = process_update(validated_data[k], data)

                    if retdata is not None:

                        # create update object
                        obj = AmbulanceUpdate(**data)
                        obj.save()

                        # append to objects list
                        instances.append(obj)

                # on last update, update ambulance instead

                # process update
                data = process_update(validated_data[-1], data)

                # save to ambulance will automatically create update
                for attr, value in data.items():
                    setattr(ambulance, attr, value)
                ambulance.save()

                # append to objects list
                instances.append(ambulance)

            # return created instances
            return instances

        except IntegrityError:
            logger.info('Integrity error in bulk ambulance update')


class AmbulanceUpdateSerializer(serializers.ModelSerializer):

    location = PointField(required=False)
    ambulance_identifier = serializers.CharField(source='ambulance.identifier', required=False)
    updated_by_username = serializers.CharField(source='updated_by.username', required=False)

    class Meta:
        list_serializer_class = AmbulanceUpdateListSerializer
        model = AmbulanceUpdate
        fields = ['id',
                  'ambulance_id',
                  'ambulance_identifier',
                  'status', 'orientation',
                  'location', 'timestamp',
                  'comment',
                  'updated_by_username', 'updated_on']
        read_only_fields = ['id',
                            'ambulance_id'
                            'ambulance_identifier',
                            'updated_by_username', 'updated_on']


# Location serializers

class LocationSerializer(serializers.ModelSerializer):
    location = PointField(required=False)

    class Meta:
        model = Location
        fields = ['id',
                  'number', 'street', 'unit', 'neighborhood',
                  'city', 'state', 'zipcode', 'country',
                  'location',
                  'name', 'type',
                  'comment', 'updated_by', 'updated_on']
        read_only_fields = ('updated_by',)

    def create(self, validated_data):

        # get current user
        user = validated_data['updated_by']

        # check credentials
        # only super can create
        if not user.is_superuser:
            raise PermissionDenied()

        return super().create(validated_data)

    def update(self, instance, validated_data):

        # get current user
        user = validated_data['updated_by']

        # check credentials
        # only super can create
        if not user.is_superuser:
            raise PermissionDenied()

        return super().update(instance, validated_data)


# AmbulanceCallTime Serializer 

class AmbulanceCallTimeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AmbulanceCallTime
        fields = ['id', 'call_id', 'ambulance_id', 'dispatch_time', 
                  'departure_time', 'patient_time', 'hospital_time', 
                  'end_time']


# Patient Serializer

class PatientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Patient
        fields = ['id', 'call_id', 'name', 'age']


# Call serializer

class CallSerializer(serializers.ModelSerializer):
    
    patient_set = PatientSerializer(many = True)
    ambulancecalltime_set = AmbulanceCallTimeSerializer(many=True)
    location = PointField(required=False)
    
    class Meta:
        model = Call
        fields = ['id', 'status', 'details', 'priority',
                  'number', 'street', 'unit', 'neighborhood',
                  'city', 'state', 'zipcode', 'country',
                  'location', 'created_at', 'ended_at', 
                  'comment', 'updated_by', 'updated_on', 
                  'ambulancecalltime_set', 'patient_set']
        read_only_fields = ['updated_by']

    def create(self, data):

        # Get current user.
        user = data['updated_by']

        # Make sure user is Super.
        if not user.is_superuser:
            raise PermissionDenied()

        return super().create(data)

    def update(self, instance, data):

        # Get current user.
        user = data['updated_by']

        # Make sure user is Super.
        if not user.is_superuser:
            # Serializer instance will always exist!
            if not user.profile.calls.filter(can_write=True, call=instance.id):
                raise PermissionDenied()

        return super().update(instance, data)
