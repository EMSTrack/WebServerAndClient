from django.utils import timezone

from django.db import models
from django.contrib.gis.db import models
from django.contrib.gis.geos import LineString, Point
from django.contrib.auth.models import AbstractUser

Tijuana = Point(-117.0382, 32.5149, srid=4326)
DefaultRoute = LineString((0, 0), (1, 1), srid=4326)

# Model schemas for the database


class Status(models.Model):
    name = models.CharField(max_length=254, unique=True)

    def __str__(self):
        return "{}".format(self.name)


class Capability(models.Model):
    name = models.CharField(max_length=254, unique=True)

    def __str__(self):
        return "{}".format(self.name)


class Ambulances(models.Model):
    license_plate = models.CharField(max_length=20)
    name = models.CharField(max_length=254, default="")

    status = models.ForeignKey(Status, on_delete=models.CASCADE, default=1)
    # location = models.PointField(srid=4326, default=Tijuana)
    orientation = models.FloatField(null=True)
    # device = models.OneToOneField(TrackableDevice, blank=True, null=True)
    priority = models.CharField(max_length=254, default="High")
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.license_plate


class Call(models.Model):
    #call metadata (status not required for now)
    active = models.BooleanField(default=False)
    status = models.CharField(max_length=254, default= "", blank=True)
    # ambulance assigned to Call (Foreign Key)
    ambulance = models.ForeignKey(Ambulances, on_delete=models.CASCADE, default=1)
    name = models.CharField(max_length=254, default = "")
    # address-related info
    residential_unit = models.CharField(max_length=254, default = "None")
    stmain_number = models.CharField(max_length=254, default = "None")
    delegation = models.CharField(max_length=254, default = "None")
    zipcode = models.CharField(max_length=254, default = "22500")
    city = models.CharField(max_length=254, default="Tijuana")
    state = models.CharField(max_length=254, default="Baja California")
    location = models.PointField(srid=4326, default=Tijuana)
    # assignment = base name and #
    assignment = models.CharField(max_length=254, default = "None")
    # short description of the patient's injury
    description = models.CharField(max_length=500, default = "None")
    # response time related info
    call_time = models.DateTimeField(default = timezone.now)
    departure_time = models.DateTimeField(blank = True, null = True)
    transfer_time = models.DateTimeField(blank = True, null = True)
    hospital_time = models.DateTimeField(blank = True, null = True)
    base_time = models.DateTimeField(blank = True, null = True)
    PRIORITIES = [('A','A'),('B','B'),('C','C'),('D','D'),('E','E')]
    priority = models.CharField(max_length=254, choices=PRIORITIES, default='A')

    def __str__(self):
        return "({}): {}, {}".format(self.priority, self.residential_unit, self.stmain_number)


class Region(models.Model):
    name = models.CharField(max_length=254, unique=True)
    center = models.PointField(srid=4326, null=True)

    def __str__(self):
        return self.name


class Hospital(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=254, default="")
    address = models.CharField(max_length=254, default="")

    def __str__(self):
        return "{}".format(self.name)


class Equipment(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=254)
    toggleable = models.BooleanField(default=0)

    def __str__(self):
        return "{}".format(self.name)


class EquipmentCount(models.Model):

    id = models.AutoField(primary_key=True)
    hospital = models.ForeignKey(Hospital, related_name='equipment',on_delete=models.CASCADE, null=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    class Meta:
        unique_together = ('hospital', 'equipment',)

    def __str__(self):
        return "Hospital: {}, Equipment: {}, Count: {}".format(self.hospital, self.equipment, self.quantity)


class Base(models.Model):
    name = models.CharField(max_length=254, unique=True)
    location = models.PointField(srid=4326, null=True)

    def __str__(self):
        return self.name


class Route(models.Model):
    name = models.CharField(max_length=50, null=False, default="Default Route Name")
    path = models.LineStringField(srid=4326, null=False, default=DefaultRoute)
    # Think about abstraction?
    type = models.CharField(max_length=50, null=False, default="Default Type")

class User(AbstractUser):
    hospitals = models.ManyToManyField(Hospital)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True, related_name="hosp_id")
    ambulance = models.ForeignKey(Ambulances, on_delete=models.CASCADE, null=True, blank=True)

class LocationPoint(models.Model):
    location = models.PointField(srid=4326, default=Tijuana)
    ambulance = models.ForeignKey(Ambulances, on_delete=models.CASCADE, default=1)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, null=True, blank=True)
    # Remove nullable in the future
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1, null=True, blank=True)
    timestamp = models.DateTimeField()
    type = models.CharField(max_length=50, null=False, default="Default Type")

    def __str__(self):
        return "Ambulance: {} at {}".format(self.ambulance.license_plate, self.location)
