# coding=utf-8

from django import forms 
from django.utils.translation import gettext_lazy as _
from .models import Torneo

from django import forms
from django.utils.translation import gettext_lazy as _

class TorneoForm(forms.Form):
    nombre = forms.CharField(
        max_length=150, 
        label=_('Tournament name'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    comienzo_inscripcion = forms.DateTimeField(
        label=_('Start of registration'),
        widget=forms.TextInput(attrs={'type':'datetime-local', 'class': 'form-control'})
    )
    fin_inscripcion = forms.DateTimeField(
        label=_('End of registration'),
        widget=forms.TextInput(attrs={'type':'datetime-local', 'class': 'form-control'})
    )
    comienzo_partidos = forms.DateTimeField(
        label=_('Start of matches'),
        widget=forms.TextInput(attrs={'type':'datetime-local', 'class': 'form-control'})
    )
    minutos_duracion_maxima_partidos = forms.IntegerField(
        label=_('Maximum match duration in minutes'),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    minutos_entre_partidos = forms.IntegerField(
        label=_('Minutes between matches'),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:  
        model = Torneo
