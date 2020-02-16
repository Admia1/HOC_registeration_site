from django.contrib.auth import  login, logout
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.templatetags.static import static
import datetime
from furl import furl
from zeep import Client
import json

from django.contrib.auth.models import User

from .models import Person, Invoice, Event, Visitor

from . import secret

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def farsi_to_english_digit(number_string):
    dic = {
    "۰" : "0",
    "۱" : "1",
    "۲" : "2",
    "۳" : "3",
    "۴" : "4",
    "۵" : "5",
    "۶" : "6",
    "۷" : "7",
    "۸" : "8",
    "۹" : "9",
    }
    for digit in dic:
        number_string = number_string.replace(digit, dic[digit])
    return number_string


def register_post_validator(post):
    for field_name in ['first_name', 'last_name', 'father_first_name', 'national_id', 'phone_number', 'parent_phone_number', 'school_name', 'school_grade', 'territory', 'programming_familiar', 'special_state','birth_year', 'birth_month', 'birth_day']:
        if field_name not in post:
            return f"field {field_name} missing from request"

    for field_name in ['first_name', 'last_name', 'phone_number', 'parent_phone_number', 'school_name']:
        if len(post[field_name])>99:
            return f"field {field_name} is too long"


    if len(post['national_id']) != 10:
        return "طول کد ملی نا معتبر است"

    for digit in post["national_id"]:
        if digit not in "0123456789۰۱۲۳۴۵۶۷۸۹":
            return "فرمت ناصحیح کد ملی"

    for digit in post['phone_number']:
        if digit not in "0123456789۰۱۲۳۴۵۶۷۸۹+":
            return "فرمت ناصحیح شماره تلفن"

    for digit in post['parent_phone_number']:
        if digit not in "0123456789۰۱۲۳۴۵۶۷۸۹+":
            return "فرمت ناصحیح شماره تلفن والدین"

    if  post['territory'] not in ['1','2','3','4']:
        return "فرمت ناصحیح ناحیه"

    if post['school_grade'] not in [str(n) for n in range(1,13)]:
        return "فرمت ناصحیح سال تحصیلی"
    return False # no error massage

#$ check national id
def register_view(request):
    template = 'registeration/register.html'
    if request.method == 'POST':
        #validation of data
        error_message = register_post_validator(request.POST)
        if not error_message:
            # if user didnt registered before
            if not Invoice.objects.filter(person__national_id = farsi_to_english_digit(request.POST['national_id']), paid=1).exists():
                # then create the user
                person = Person.objects.create(
                first_name = request.POST['first_name'],
                last_name = request.POST['last_name'],
                father_first_name = request.POST['father_first_name'],
                national_id = farsi_to_english_digit(request.POST['national_id']),
                phone_number = request.POST['phone_number'],
                parent_phone_number = request.POST['parent_phone_number'],
                school_name  = request.POST['school_name'],
                school_grade = int(request.POST['school_grade']),
                territory = int(request.POST['territory']),
                birthday_date = f"{request.POST['birth_year']} - {request.POST['birth_month']} - {request.POST['birth_day']}",
                programming_familiar = request.POST['programming_familiar'],
                special_state = request.POST['special_state'])

                if 'has_laptop' in request.POST:
                    if request.POST['has_laptop']:
                        person.has_laptop = True

                person.save()

                ## $$$ purchase ticket
                if person.has_laptop:
                    return purchase_view(request, 1, person)
                else:
                    return purchase_view(request, 2, person)

            else:
                # registered and payed before
                return render(request,template,{'error_message': "کد ملی از قبل وجود دارد"})
        else:
            # error on data
            return render(request,template,{'error_message': error_message})

    return render(request,template)

def home_view(request):
    ip=get_client_ip(request)
    if(ip != '127.0.0.1'):
        Visitor.objects.create(ip=get_client_ip(request))
    template = 'registeration/index.html'
    return render(request,template)

def verify_view(request):
    MERCHANT = secret.MERCHANT
    template = 'registeration/message.html'
    if request.GET.get('Status') == 'OK':
        authority = request.GET['Authority']
        try:
            invoice = Invoice.objects.get(authority=authority)
        except:
            return render(request,template,{'message': 'خطایی رخ داده است'})

        client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
        result = client.service.PaymentVerification(MERCHANT, invoice.authority, invoice.amount)
        if result.Status == 100 or result.Status == 101:
            #payed
            invoice = Invoice.objects.get(authority=request.GET['Authority'])
            invoice.refid = result.RefID
            invoice.active = 1
            invoice.paid = 1
            invoice.save()

            for o_invoice in Invoice.objects.filter(person=invoice.person, event=invoice.event, active=1, paid=0):
                o_invoice.active=0
                o_invoice.save()
            return render(request,template,{'message': "ثبت نام شما با موفقیت به پایان رسید"})

        else:
            #failed to pay
            return render(request,template,{'message':"پرداخت نا موفق"})

    return render(request,template,{'message':"پرداخت نا موفق"})


def purchase_view(request, event_pk, person):
    invoice_cleaner()
    try:
        event  = Event.objects.get(pk = event_pk)
    except:
        return HttpResponse("این رویداد وجود ندارد")


    if Invoice.objects.filter(event=event, active=1).count() >= event.capacity:
        invoice_cleaner()# :/
        if Invoice.objects.filter(event=event, active=1).count() >= event.capacity:
            return HttpResponse("ظرفیت این رویداد به اتمام رسیده است")

    amount  = event.price
    invoice = Invoice.objects.create(person=person, event=event, amount=amount)

    if Invoice.objects.filter(event=event, active=1).count() > event.capacity:
        invoice.active=0
        invoice.save()
        return HttpResponse("ظرفیت این رویداد به اتمام رسیده است")

    return send_to_zarin(request, invoice)




def send_to_zarin(request, invoice):
    MERCHANT = secret.MERCHANT
    client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
    description = "هزینه ثبتنام همایش زنگ برنامه نویسی دانشگاه شیراز"              # Required
    email  = "no email"                                   # Optional
    mobile = invoice.person.phone_number                  # Optional
    CallbackURL = furl(request.build_absolute_uri(reverse("registeration:verify")))

    amount = invoice.amount

    result = client.service.PaymentRequest(MERCHANT, amount, description, email, mobile, CallbackURL)
    if result.Status == 100:
        invoice.authority = result.Authority
        invoice.save()
        return redirect(f'https://www.zarinpal.com/pg/StartPay/{result.Authority}/ZarinGate' )
    else:
        invoice.active = 0
        invoice.save()
        return render(request, template, {'error_message':'خطای درگاه'})

def error(request):
    return HttpResponse("error")


def invoice_cleaner():
    for invoice in Invoice.objects.filter(active=1, paid=0):
        if  datetime.datetime.now(datetime.timezone.utc) - invoice.created_date > datetime.timedelta(hours=1):
            invoice.active=0
            invoice.save()
