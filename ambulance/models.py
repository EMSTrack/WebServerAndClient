import logging
from enum import Enum

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.utils import timezone
from django.urls import reverse
from django.template.defaulttags import register

from emstrack.latlon import calculate_orientation, calculate_distance, stationary_radius
from emstrack.models import AddressModel, UpdatedByModel, defaults

logger = logging.getLogger(__name__)


# filters

@register.filter
def get_ambulance_status(key):
    return AmbulanceStatus[key].value


@register.filter
def get_ambulance_capability(key):
    return AmbulanceCapability[key].value


@register.filter
def get_location_type(key):
    return LocationType[key].value


@register.filter
def get_call_priority(key):
    return CallPriority[key].value


# Ambulance location models


# Ambulance model

class AmbulanceStatus(Enum):
    UK = 'Unknown'
    AV = 'Available'
    OS = 'Out of service'
    PB = 'Patient bound'
    AP = 'At patient'
    HB = 'Hospital bound'
    AH = 'At hospital'


class AmbulanceCapability(Enum):
    B = 'Basic'
    A = 'Advanced'
    R = 'Rescue'


class Ambulance(UpdatedByModel):

    # ambulance properties
    identifier = models.CharField(max_length=50, unique=True)

    # TODO: Should we add an active flag?

    AMBULANCE_CAPABILITY_CHOICES = \
        [(m.name, m.value) for m in AmbulanceCapability]
    capability = models.CharField(max_length=1,
                                  choices=AMBULANCE_CAPABILITY_CHOICES)

    # status
    AMBULANCE_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceStatus]
    status = models.CharField(max_length=2,
                              choices=AMBULANCE_STATUS_CHOICES,
                              default=AmbulanceStatus.UK.name)

    # location
    orientation = models.FloatField(default=0)
    location = models.PointField(srid=4326, default=defaults['location'])

    # timestamp
    timestamp = models.DateTimeField(default=timezone.now)

    # location client
    location_client = models.ForeignKey('login.Client',
                                        on_delete=models.CASCADE,
                                        blank=True, null=True,
                                        related_name='location_client_set')

    # default value for _loaded_values
    _loaded_values = None

    @classmethod
    def from_db(cls, db, field_names, values):

        # call super
        instance = super(Ambulance, cls).from_db(db, field_names, values)

        # store the original field values on the instance
        instance._loaded_values = dict(zip(field_names, values))

        # return instance
        return instance

    def save(self, *args, **kwargs):

        # creation?
        created = self.pk is None

        # loaded_values?
        loaded_values = self._loaded_values is not None

        # has location changed?
        has_moved = False
        if (not loaded_values) or \
                calculate_distance(self._loaded_values['location'], self.location) > stationary_radius:
            has_moved = True

        # calculate orientation only if location has changed and orientation has not changed
        if has_moved and loaded_values and self._loaded_values['orientation'] == self.orientation:
            # TODO: should we allow for a small radius before updating direction?
            self.orientation = calculate_orientation(self._loaded_values['location'], self.location)
            logger.debug('< {} - {} = {}'.format(self._loaded_values['location'],
                                                 self.location,
                                                 self.orientation))

        logger.debug('loaded_values: {}'.format(loaded_values))
        logger.debug('_loaded_values: {}'.format(self._loaded_values))
        logger.debug('self.location_client: {}'.format(self.location_client))

        # location_client changed?
        if self.location_client is None:
            location_client_id = None
        else:
            location_client_id = self.location_client.id
        location_client_changed = False
        if loaded_values and location_client_id != self._loaded_values['location_client_id']:
            location_client_changed = True

        logger.debug('location_client_changed: {}'.format(location_client_changed))
        # TODO: Check if client is logged with ambulance if setting location_client

        # if comment, status or location changed
        model_changed = False
        if has_moved or \
                self._loaded_values['status'] != self.status or \
                self._loaded_values['comment'] != self.comment:

            # save to Ambulance
            super().save(*args, **kwargs)

            logger.debug('SAVED')

            # save to AmbulanceUpdate
            data = {k: getattr(self, k)
                    for k in ('status', 'orientation',
                              'location', 'timestamp',
                              'comment', 'updated_by', 'updated_on')}
            data['ambulance'] = self
            obj = AmbulanceUpdate(**data)
            obj.save()

            logger.debug('UPDATE SAVED')

            # model changed
            model_changed = True

        # if identifier or capability changed
        # NOTE: self._loaded_values is NEVER None because has_moved is True
        elif (location_client_changed or
              self._loaded_values['identifier'] != self.identifier or
              self._loaded_values['capability'] != self.capability):

            # save only to Ambulance
            super().save(*args, **kwargs)

            logger.debug('SAVED')

            # model changed
            model_changed = True

        # Did the model change?
        if model_changed:

            # publish to mqtt
            from mqtt.publish import SingletonPublishClient
            SingletonPublishClient().publish_ambulance(self)

            logger.debug('PUBLISHED ON MQTT')

        # just created?
        if created:
            # invalidate permissions cache
            from login.permissions import cache_clear
            cache_clear()

    def delete(self, *args, **kwargs):

        # remove from mqtt
        from mqtt.publish import SingletonPublishClient
        SingletonPublishClient().remove_ambulance(self)

        # invalidate permissions cache
        from login.permissions import cache_clear
        cache_clear()

        # delete from Ambulance
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('ambulance:detail', kwargs={'pk': self.id})

    def __str__(self):
        return ('Ambulance {}(id={}) ({}) [{}]:\n' +
                '    Status: {}\n' +
                '  Location: {} @ {}\n' +
                ' LocClient: {}\n' +
                '   Updated: {} by {}').format(self.identifier,
                                               self.id,
                                               AmbulanceCapability[self.capability].value,
                                               self.comment,
                                               AmbulanceStatus[self.status].value,
                                               self.location,
                                               self.timestamp,
                                               self.location_client,
                                               self.updated_by,
                                               self.updated_on)


class AmbulanceUpdate(models.Model):
    # ambulance id
    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    # ambulance status
    AMBULANCE_STATUS_CHOICES = \
        [(m.name, m.value) for m in AmbulanceStatus]
    status = models.CharField(max_length=2,
                              choices=AMBULANCE_STATUS_CHOICES,
                              default=AmbulanceStatus.UK.name)

    # location
    orientation = models.FloatField(default=0)
    location = models.PointField(srid=4326, default=defaults['location'])

    # timestamp, indexed
    timestamp = models.DateTimeField(db_index=True, default=timezone.now)

    # comment
    comment = models.CharField(max_length=254, null=True, blank=True)

    # updated by
    updated_by = models.ForeignKey(User,
                                   on_delete=models.CASCADE)
    updated_on = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(
                fields=['ambulance', 'timestamp'],
                name='ambulance_timestamp_idx',
            ),
        ]


# Call related models

class CallPriority(Enum):
    A = 'Resucitation'
    B = 'Emergent'
    C = 'Urgent'
    D = 'Less urgent'
    E = 'Not urgent'

class CallStatus(Enum):
    O = 'Ongoing'
    P = 'Pending'
    F = 'Finished'

class Call(AddressModel, UpdatedByModel):

    # status
    CALL_STATUS_CHOICES = \
        [(m.name, m.value) for m in CallStatus]
    status = models.CharField(max_length=1,
                              choices=CALL_STATUS_CHOICES,
                              default=CallStatus.P.name)

    # details
    details = models.CharField(max_length=500, default="")

    # call priority
    CALL_PRIORITY_CHOICES = \
        [(m.name, m.value) for m in CallPriority]
    priority = models.CharField(max_length=1,
                                choices=CALL_PRIORITY_CHOICES,
                                default=CallPriority.E.name)

    # created at
    created_at = models.DateTimeField(auto_now_add=True)

    # ended at
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return "{} ({})".format(self.location, self.priority)


class AmbulanceCallTime(models.Model):

    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    ambulance = models.ForeignKey(Ambulance,
                                  on_delete=models.CASCADE)

    dispatch_time = models.DateTimeField(null=True, blank=True)
    departure_time = models.DateTimeField(null=True, blank=True)
    patient_time = models.DateTimeField(null=True, blank=True)
    hospital_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('call', 'ambulance')


# Patient might be expanded in the future

class Patient(models.Model):
    """
    A model that provides patient fields.
    """

    call = models.ForeignKey(Call,
                             on_delete=models.CASCADE)

    name = models.CharField(max_length=254, default="")
    age = models.IntegerField(null=True)


# Location related models

# noinspection PyPep8
class LocationType(Enum):
    b = 'Base'
    a = 'AED'
    o = 'Other'


class Location(AddressModel, UpdatedByModel):
    # location name
    name = models.CharField(max_length=254, unique=True)

    # location type
    LOCATION_TYPE_CHOICES = \
        [(m.name, m.value) for m in LocationType]
    type = models.CharField(max_length=1,
                            choices=LOCATION_TYPE_CHOICES,
                            default=LocationType.o.name)

    # location
    location = models.PointField(srid=4326, null=True)

    def get_absolute_url(self):
        return reverse('ambulance:location_detail', kwargs={'pk': self.id})

    def __str__(self):
        return "{} @{} ({})".format(self.name, self.location, self.comment)


# THOSE NEED REVIEWING

class Region(models.Model):
    name = models.CharField(max_length=254, unique=True)
    center = models.PointField(srid=4326, null=True)

    def __str__(self):
        return self.name
