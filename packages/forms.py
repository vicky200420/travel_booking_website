from django import forms

from .models import Category


class PackageSearchForm(forms.Form):
    SORT_CHOICES = [
        ('', 'Recommended'),
        ('price_low', 'Lowest Price'),
        ('price_high', 'Highest Price'),
        ('rating_high', 'Highest Rated'),
        ('most_popular', 'Most Popular'),
        ('newest', 'Newest'),
    ]

    DURATION_CHOICES = [
        ('', 'Any Duration'),
        ('1_3', '1–3 Days'),
        ('4_7', '4–7 Days'),
        ('8_14', '8–14 Days'),
        ('15+', '15+ Days'),
    ]

    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + [(c.value, c.label) for c in Category],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    destination = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Destination, city or country',
            'autocomplete': 'off',
        })
    )
    country = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Country',
            'autocomplete': 'off',
        })
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
    duration = forms.ChoiceField(
        choices=DURATION_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_rating = forms.IntegerField(
        required=False, min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1, 'max': 5,
            'placeholder': 'Min rating',
        })
    )
    featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
