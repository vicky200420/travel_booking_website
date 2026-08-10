from django import forms


class BookingForm(forms.Form):
    adults = forms.IntegerField(
        min_value=1, max_value=9, initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 1, 'max': 9,
        })
    )
    children = forms.IntegerField(
        min_value=0, max_value=9, initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 0, 'max': 9,
        })
    )
    infants = forms.IntegerField(
        min_value=0, max_value=9, initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 0, 'max': 9,
        })
    )

    check_in = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
        })
    )
    check_out = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
        })
    )
    rooms = forms.IntegerField(
        required=False, min_value=1, max_value=10, initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 'min': 1, 'max': 10,
        })
    )

    travel_start = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
        })
    )
    travel_end = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
        })
    )

    contact_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Full name',
        })
    )
    contact_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'Email address',
        })
    )
    contact_phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Phone number',
        })
    )
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 3,
            'placeholder': 'Any special requests or requirements...',
        })
    )

    def __init__(self, *args, **kwargs):
        self.booking_type = kwargs.pop('booking_type', None)
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)

        if self.booking_type == 'Flight':
            self.fields.pop('check_in')
            self.fields.pop('check_out')
            self.fields.pop('rooms')
            self.fields.pop('travel_start')
            self.fields.pop('travel_end')
        elif self.booking_type == 'Hotel':
            self.fields.pop('travel_start')
            self.fields.pop('travel_end')
        elif self.booking_type == 'Package':
            self.fields.pop('check_in')
            self.fields.pop('check_out')
            self.fields.pop('rooms')
        elif self.booking_type is None:
            self.fields.pop('check_in')
            self.fields.pop('check_out')
            self.fields.pop('rooms')
            self.fields.pop('travel_start')
            self.fields.pop('travel_end')

    def clean(self):
        cleaned = super().clean()
        if self.booking_type == 'Hotel':
            check_in = cleaned.get('check_in')
            check_out = cleaned.get('check_out')
            if not check_in:
                self.add_error('check_in', 'Check-in date is required.')
            if not check_out:
                self.add_error('check_out', 'Check-out date is required.')
            if check_in and check_out and check_out <= check_in:
                self.add_error('check_out', 'Check-out must be after check-in.')
        elif self.booking_type == 'Package':
            start = cleaned.get('travel_start')
            end = cleaned.get('travel_end')
            if not start:
                self.add_error('travel_start', 'Travel start date is required.')
            if not end:
                self.add_error('travel_end', 'Travel end date is required.')
            if start and end and end <= start:
                self.add_error('travel_end', 'End date must be after start date.')

        adults = cleaned.get('adults', 0)
        children = cleaned.get('children', 0)
        infants = cleaned.get('infants', 0)
        total = adults + children + infants
        if total < 1:
            self.add_error('adults', 'At least 1 traveler is required.')
        if total > 20:
            self.add_error('adults', 'Maximum 20 travelers allowed per booking.')

        return cleaned
