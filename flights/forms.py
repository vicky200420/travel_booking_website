from django import forms

from .models import Flight


class FlightSearchForm(forms.Form):
    SORT_CHOICES = [
        ('price_low', 'Lowest Price'),
        ('price_high', 'Highest Price'),
        ('fastest', 'Fastest Flight'),
        ('earliest_departure', 'Earliest Departure'),
        ('latest_departure', 'Latest Departure'),
    ]

    departure_city = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'From where?',
            'autocomplete': 'off',
        })
    )
    destination_city = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Where to?',
            'autocomplete': 'off',
        })
    )
    departure_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    return_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    travellers = forms.IntegerField(
        required=False, min_value=1, max_value=10, initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1, 'max': 10,
        })
    )
    cabin_class = forms.ChoiceField(
        choices=[('', 'All Classes')] + list(Flight.CabinClass.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min',
            'min': 0,
        })
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max',
            'min': 0,
        })
    )
    non_stop = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    refundable = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_travellers(self):
        val = self.cleaned_data.get('travellers')
        if val and val < 1:
            return 1
        return val or 1
