from django.db import models
from django.contrib.auth.models import User


class Person(models.Model):

    first_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    father_first_name =  models.CharField(max_length = 100)
    national_id = models.CharField(max_length = 100)
    phone_number = models.CharField(max_length = 100)

    parent_phone_number = models.CharField(max_length = 100)

    school_name = models.CharField(max_length = 100)
    school_grade = models.IntegerField()
    territory  = models.IntegerField()
    has_laptop = models.BooleanField(default=False)

    birthday_date = models.CharField(max_length=50)

    programming_familiar = models.TextField()
    special_state = models.TextField()

    def __str__(self):
        return self.first_name + " " + self.last_name

class Event(models.Model):
    name = models.CharField(max_length=200)
    price = models.IntegerField(default=5000)#tooman.
    capacity = models.IntegerField(default=30)#People

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Invoice(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    event  = models.ForeignKey(Event, on_delete=models.PROTECT)
    amount = models.IntegerField(default=0)# tooman
    active = models.IntegerField(default=1)# 0: deactive     , 1: active
    paid   = models.IntegerField(default=0)# 0: never_paid , 1: $$$

    authority   = models.CharField(max_length = 200, default = "none")
    refid       = models.CharField(max_length = 200, default = "none")

    def is_successful(self):
        return self.status == 0

    def __str__(self):
        if self.paid:
            return str(self.amount) + "$"
        if not self.active:
            return "خارج از دور"
        return "در حال پرداخت"


class Visitor(models.Model):
    ip = models.CharField(max_length=20)
    visit_time = models.DateTimeField(auto_now=True)
