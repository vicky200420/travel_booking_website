from django import forms


class HotelSearchForm(forms.Form):
    SORT_CHOICES = [
        ('', 'Recommended'),
        ('price_low', 'Lowest Price'),
        ('price_high', 'Highest Price'),
        ('rating_high', 'Highest Rating'),
        ('newest', 'Newest'),
    ]

    destination = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Where are you going?',
            'autocomplete': 'off',
        })
    )
    check_in = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    check_out = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        })
    )
    guests = forms.IntegerField(
        required=False, min_value=1, max_value=20, initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1, 'max': 20,
        })
    )
    rooms = forms.IntegerField(
        required=False, min_value=1, max_value=10, initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1, 'max': 10,
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
    star_rating = forms.IntegerField(
        required=False, min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1, 'max': 5,
            'placeholder': 'Min stars',
        })
    )
    featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    wifi = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pool = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    parking = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    spa = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    gym = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    restaurant = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    ac = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    breakfast = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pet_friendly = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_guests(self):
        val = self.cleaned_data.get('guests')
        return val or 1

    def clean_rooms(self):
        val = self.cleaned_data.get('rooms')
        return val or 1
