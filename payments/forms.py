from django import forms

from .models import Payment


class PaymentVerifyForm(forms.Form):
    razorpay_order_id = forms.CharField(required=False)
    razorpay_payment_id = forms.CharField(required=False)
    razorpay_signature = forms.CharField(required=False)
    payment_intent_id = forms.CharField(required=False)
    status = forms.CharField(required=False)
    payment_method = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        razorpay = all([
            cleaned.get('razorpay_order_id'),
            cleaned.get('razorpay_payment_id'),
            cleaned.get('razorpay_signature'),
        ])
        stripe = cleaned.get('payment_intent_id')
        if not razorpay and not stripe:
            raise forms.ValidationError('No valid payment data provided.')
        return cleaned


class PaymentFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All Statuses')] + [
        (s.value, s.label) for s in Payment.Status
    ]
    GATEWAY_CHOICES = [('', 'All Gateways')] + [
        (g.value, g.label) for g in Payment.Gateway
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    gateway = forms.ChoiceField(
        choices=GATEWAY_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
