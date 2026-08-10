"""Dashboard — forms for the settings tabs."""
from django import forms
from django.contrib.auth.password_validation import validate_password

from accounts.models import CustomUser

from .models import UserProfile

BUDGET_CHOICES = [
    ('budget', 'Budget friendly'),
    ('mid', 'Mid-range'),
    ('luxury', 'Luxury'),
    ('unlimited', 'No limit'),
]

SEAT_CHOICES = [
    ('', 'No preference'),
    ('window', 'Window'),
    ('aisle', 'Aisle'),
    ('middle', 'Middle'),
    ('legroom', 'Extra legroom'),
]

MEAL_CHOICES = [
    ('', 'No preference'),
    ('veg', 'Vegetarian'),
    ('non_veg', 'Non-vegetarian'),
    ('vegan', 'Vegan'),
    ('halal', 'Halal'),
    ('jain', 'Jain'),
]

AMENITY_CHOICES = [
    ('wifi', 'WiFi'),
    ('pool', 'Swimming Pool'),
    ('spa', 'Spa'),
    ('gym', 'Gym'),
    ('restaurant', 'Restaurant'),
    ('breakfast', 'Breakfast Included'),
    ('parking', 'Parking'),
    ('pet', 'Pet Friendly'),
]

FORM_CONTROL = {'class': 'form-control'}
FORM_CHECK = {'class': 'form-check-input'}


class DashboardProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone_number',
                  'date_of_birth', 'address', 'city', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs=FORM_CONTROL),
            'last_name': forms.TextInput(attrs=FORM_CONTROL),
            'phone_number': forms.TextInput(attrs=FORM_CONTROL),
            'date_of_birth': forms.DateInput(
                attrs={**FORM_CONTROL, 'type': 'date'}
            ),
            'address': forms.Textarea(attrs={**FORM_CONTROL, 'rows': 2}),
            'city': forms.TextInput(attrs=FORM_CONTROL),
            'country': forms.TextInput(attrs=FORM_CONTROL),
        }


class DashboardPictureForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['profile_image']
        widgets = {
            'profile_image': forms.FileInput(
                attrs={'class': 'form-control', 'accept': 'image/*'}
            ),
        }


class DashboardPasswordForm(forms.Form):
    current_password = forms.CharField(
        label='Current password',
        widget=forms.PasswordInput(
            attrs={**FORM_CONTROL, 'autocomplete': 'current-password'}
        ),
    )
    new_password = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(
            attrs={**FORM_CONTROL, 'autocomplete': 'new-password'}
        ),
    )
    confirm_password = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(
            attrs={**FORM_CONTROL, 'autocomplete': 'new-password'}
        ),
    )

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if new and confirm and new != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        if new:
            try:
                validate_password(new)
            except forms.ValidationError as exc:
                self.add_error('new_password', exc)
        return cleaned


class TravelPreferencesForm(forms.Form):
    budget_range = forms.ChoiceField(
        choices=BUDGET_CHOICES, widget=forms.Select(attrs=FORM_CONTROL)
    )
    seat_preference = forms.ChoiceField(
        choices=SEAT_CHOICES, required=False,
        widget=forms.Select(attrs=FORM_CONTROL),
    )
    meal_preference = forms.ChoiceField(
        choices=MEAL_CHOICES, required=False,
        widget=forms.Select(attrs=FORM_CONTROL),
    )
    airline_preferences = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={**FORM_CONTROL, 'placeholder': 'e.g. IndiGo, Air India'}
        ),
    )
    frequent_flyer = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={**FORM_CONTROL, 'placeholder': 'Frequent flyer number'}
        ),
    )
    special_needs = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={**FORM_CONTROL, 'placeholder': 'Accessibility or medical needs'}
        ),
    )
    hotel_amenities = forms.MultipleChoiceField(
        choices=AMENITY_CHOICES, required=False, label='Preferred hotel amenities',
        widget=forms.CheckboxSelectMultiple(attrs=FORM_CHECK),
    )

    @classmethod
    def from_profile(cls, profile):
        prefs = {**UserProfile.DEFAULT_TRAVEL_PREFS, **profile.travel_preferences}
        return cls(initial=prefs)


class NotificationPreferencesForm(forms.Form):
    email_notifications = forms.BooleanField(
        required=False, label='Email notifications',
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    push_notifications = forms.BooleanField(
        required=False, label='Push notifications',
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    booking_updates = forms.BooleanField(
        required=False, label='Booking updates',
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    payment_alerts = forms.BooleanField(
        required=False, label='Payment alerts',
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    trip_reminders = forms.BooleanField(
        required=False, label='Trip reminders',
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )
    promotions = forms.BooleanField(
        required=False, label='Promotions & offers',
        widget=forms.CheckboxInput(attrs=FORM_CHECK),
    )

    @classmethod
    def from_profile(cls, profile):
        prefs = {**UserProfile.DEFAULT_NOTIF_PREFS, **profile.notification_preferences}
        return cls(initial=prefs)
