from django import forms
from django.contrib.auth.models import User
from .models import Partido, PerfilUsuario, Pais


class ResultadoForm(forms.ModelForm):
    class Meta:
        model = Partido
        fields = ['goles_local', 'goles_visitante', 'hubo_penales', 'penales_local', 'penales_visitante', 'jugado']
        widgets = {
            'goles_local': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 20}),
            'goles_visitante': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 20}),
            'hubo_penales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'penales_local': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 30}),
            'penales_visitante': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 30}),
            'jugado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        data = super().clean()
        if data.get('hubo_penales'):
            if data.get('penales_local') is None or data.get('penales_visitante') is None:
                raise forms.ValidationError('Debes ingresar el resultado de los penales.')
        return data


class PerfilForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = ['campeon']
        widgets = {
            'campeon': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campeon'].queryset = Pais.objects.all()
        self.fields['campeon'].empty_label = '-- Selecciona un campeón --'
        self.fields['campeon'].label = 'Campeón del Mundial'
