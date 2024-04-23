
#from django.shortcuts import render
from django.utils.translation import activate
from .models import UserSettings

def activate_language(request):
    myLanguage = request.session.get('myLanguage')
    if myLanguage is None:
        # Si no se ha establecido un idioma en la sesión, intenta obtenerlo de UserSettings
        user = request.user
        if user.is_authenticated:  # Verifica si el usuario está autenticado
            try:
                user_settings = UserSettings.objects.get(user=user)
                myLanguage = user_settings.language
            except UserSettings.DoesNotExist:
                pass  # Si no hay configuración de idioma para el usuario, continúa sin cambios

    if myLanguage is not None:
        activate(myLanguage)
