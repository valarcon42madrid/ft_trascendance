# coding=utf-8

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout 
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout 
from .forms import UserCreationForm, LoginForm
from general.views import activate_language
from torneos.views import torneo_jugar, proximos_torneos
import requests
from django.contrib.auth.models import User
import os

from django.shortcuts import render
from django_otp.plugins.otp_totp.models import TOTPDevice
import pyotp
import qrcode

from django.conf import settings
import jwt
from datetime import datetime, timedelta

from general.models import UserSettings
from .forms import UserSettingsForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect

from django.http import HttpResponse
from django.template import loader

def change_language(request, language):
    request.session['myLanguage'] = language
    if request.user.is_authenticated:
        try:
            user_settings = UserSettings.objects.get(user=request.user)
            user_settings.language = language
            user_settings.save()
            request.session['myLanguage'] = user_settings.language
        except UserSettings.DoesNotExist:
            # Si no hay configuración de idioma para el usuario, crea una nueva
            UserSettings.objects.create(user=request.user, language=language, two_factor_auth_enabled=False, alias="")
    return redirect('home')

def change_en(request):
    return change_language(request, 'en')

def change_es(request):
    return change_language(request, 'es')

def change_fr(request):
    return change_language(request, 'fr')
    
# Create your views here.
# Home page
def home(request):
    activate_language(request)
    jugar = False
    hayProximosTorneos = False
    proximosTorneos = []
    if request.user.is_authenticated:
        res = torneo_jugar(request.user.id)
        jugar = res['ok']
        proximosTorneos = proximos_torneos(request.user.id)
        hayProximosTorneos = (len(proximosTorneos) > 0)
        #print(proximosTorneos)
        #print(jugar)
    context = { 'jugar': jugar, 
                    'proximosTorneos': proximosTorneos, 
                    'hayProximosTorneos': hayProximosTorneos }
    return render(request, 'singlepage/index.html', context)



def user_signup(request):
    activate_language(request)
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'redirect_url': '/'})
        else:
            errors = form.errors.as_json()
            return JsonResponse({'errors': errors}, status=400)
    else:
        form = UserCreationForm()
        template = loader.get_template('base/signup_t.html')
        context = {
            'form': form
        }
        return HttpResponse(template.render(context, request))

def google_code(request):
    url = request.build_absolute_uri()
    url_obj = requests.utils.urlparse(url)

    username = url_obj.query.split("=")[1] if "username" in url_obj.query else None
    return render(request, 'base/google_code_t.html', {'username': username})

# Google Authenticator page
def setup_google_authenticator(request):
    activate_language(request)
    if request.method == 'POST':
        username = request.POST.get('username')
        # Obtener el secreto del usuario
        device = TOTPDevice.objects.get(user=User.objects.get(username=username), confirmed=True)
        secreto = device.key
        codigo = request.POST.get('verification_code')
        # Verificar el código
        totp = pyotp.TOTP(secreto)
        if totp.verify(codigo):
            login(request, User.objects.get(username=username))
        return redirect('home')
    else:
        return render(request, 'base/google_t.html')

# API page
def user_api2(request):
    return render(request, 'base/api_t.html', {'code': request.GET.get('code')})

def user_api(request):
    activate_language(request)
    url = request.build_absolute_uri()
    url_obj = requests.utils.urlparse(url)

    authorization_code = url_obj.query.split("=")[2] if "code" in url_obj.query else None
    # Parámetros necesarios para la solicitud POST
    hostname = url_obj.query.split("=")[1] if "hostname" in url_obj.query else None
    partes = hostname.split('&')
    hostname = partes[0]
    client_id = os.getenv('ID')
    client_secret = os.getenv('SECRET')
    code =  authorization_code
    redirect_uri = 'https://' + str(hostname) + '/api2'  # Tu URL de redirección
    if code:
        # Realiza la solicitud POST a la URL de token de acceso
        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        response = requests.post('https://api.intra.42.fr/oauth/token', data=data)

        if response.status_code == 200:

            token = response.json().get('access_token')
            headers = {
                'Authorization': f'Bearer {token}'
            }
            # Hace una solicitud GET para obtener los detalles del usuario
            response = requests.get('https://api.intra.42.fr/v2/me', headers=headers)

            if response.status_code == 200:
                username = response.json().get('login')
                fa = None
                # Verificar si el usuario ya existe
                if not User.objects.filter(username=username).exists():
                    usuario = User.objects.create_user(username=username, email='', password=token)
                    usuario.save()
                else:
                    user, created = User.objects.get_or_create(username=username)
                    user.set_password(token)
                    user.save()
                user = authenticate(request, username=username, password=token)
                # Verificar si el usuario tiene habilitado 2FA
                user_settings, created = UserSettings.objects.get_or_create(user=user)
                if created:
                    user_settings.save()
                elif not created:
                    user2 = User.objects.get(username=username)
                    fa = UserSettings.objects.get(user=user2).two_factor_auth_enabled
                if user:
                    # Generar token
                    token = generate_jwt_token(user)
                    request.session['token'] = token
                    # 2FA
                    if fa:
                        return render(request, 'singlepage/index.html', {'username2': username})
                    else:
                        login(request, user)
                        return redirect('home')
    return render(request, 'singlepage/index.html')

# login page
def user_login(request):
    activate_language(request)
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            fa = None
            user = authenticate(request, username=username, password=password)
            if user:
                # Verificar si el usuario tiene habilitado 2FA
                user_settings, created = UserSettings.objects.get_or_create(user=user)
                if created:
                    user_settings.save()
                elif not created:
                    user2 = User.objects.get(username=username)
                    if user_settings.language != "no":
                        request.session['myLanguage'] = user_settings.language
                    fa = UserSettings.objects.get(user=user2).two_factor_auth_enabled
                # Generar token
                token = generate_jwt_token(user)
                request.session['token'] = token
                # 2FA
                if fa:
                    return JsonResponse({'redirect_url': '/', 'username2': username})
                else:
                    login(request, user)
                    return JsonResponse({'redirect_url': '/'})
            else:
                errors = form.errors.as_json()
                return JsonResponse({'errors': errors}, status=400)
                
    else:
        form = LoginForm()
    # Si la solicitud no es POST, simplemente devolver el HTML para el formulario
    return render(request, 'base/login_t.html', {'form': form})

def generate_jwt_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

# logout page
def user_logout(request):
    activate_language(request)
    logout(request)
    return render(request, 'singlepage/index.html')

@login_required
def doble_factor(request):
    if 'token' in request.session:
        token = request.session['token']
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload['user_id']
            user = User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expirado'},status=400)
    estado_2fa = UserSettings.objects.get(user=request.user).two_factor_auth_enabled
    if not estado_2fa:
        # Si 2FA no está habilitado, mostrar el QR directamente
        user = request.user
        secret = pyotp.random_base32()
        qr_path = 'static/{}_qr.png'.format(user.username)
        # Si no existe el dispositivo, se crea
        if not TOTPDevice.objects.filter(user=user).exists():
            device = TOTPDevice.objects.create(user=user)
            device.key = secret
            device.save()
            otp_url = pyotp.totp.TOTP(secret).provisioning_uri(user.username, issuer_name='42')
            # Generar QR
            qr = qrcode.make(otp_url)
            qr.save(qr_path)
            user_settings, created = UserSettings.objects.get_or_create(user=user)
            user_settings.two_factor_auth_enabled = True
            user_settings.save()
        if request.method == 'GET':
            return render(request, 'base/google_t.html', {'qr_path': qr_path, 'username': user.username})
        return render(request, 'singlepage/index.html', {'qr_path': qr_path, 'username': user.username})
    else:
        user = request.user
        qr_path = 'static/{}_qr.png'.format(user.username)
        if request.method == 'GET':
            return render(request, 'base/google_t.html', {'qr_path': qr_path, 'username': user.username})
        return render(request, 'singlepage/index.html', {'qr_path': qr_path, 'username': user.username})

