from django.contrib import admin
from .models import Event, Invoice, Person, Visitor


admin.site.register(Event)
admin.site.register(Invoice)
admin.site.register(Person)
admin.site.register(Visitor)
