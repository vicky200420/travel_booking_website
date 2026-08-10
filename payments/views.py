"""Payments — views (thin).

Views only glue HTTP to the services layer; all business logic lives in
:mod:`payments.services` and :mod:`payments.gateway`.
"""
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, TemplateView, View

from bookings.models import Booking

from .forms import PaymentFilterForm
from .models import Payment
from .services import PaymentService, RazorpayService

CURRENCY_SYMBOLS = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£'}


def _currency_symbol(currency):
    return CURRENCY_SYMBOLS.get(currency, '₹')


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class PaymentCheckoutView(LoginRequiredMixin, TemplateView):
    """Step 1–4: create booking → create order → pass order ID → open popup."""

    template_name = 'payments/checkout.html'

    def dispatch(self, request, *args, **kwargs):
        booking_id = request.GET.get('booking')
        if not booking_id:
            messages.error(request, 'No booking specified.')
            return redirect('booking_history')

        self.booking = get_object_or_404(
            Booking, booking_id=booking_id, user=request.user
        )

        if self.booking.payment_status == 'Paid' or self.booking.status == 'Completed':
            messages.info(request, 'This booking is already paid.')
            return redirect('booking_detail', booking_id=booking_id)
        if self.booking.status == 'Cancelled':
            messages.error(request, 'Cancelled bookings cannot be paid for.')
            return redirect('booking_detail', booking_id=booking_id)

        gateway_name = request.GET.get('gateway', settings.DEFAULT_PAYMENT_GATEWAY)

        try:
            self.payment = PaymentService.initiate_payment(self.booking, gateway_name)
        except Exception as exc:
            messages.error(
                request,
                f'Unable to initiate payment. Please try again. ({exc})',
            )
            return redirect('booking_detail', booking_id=booking_id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.booking
        payment = self.payment

        context.update(
            booking=booking,
            payment=payment,
            gateway=payment.gateway,
            gateway_key=settings.RAZORPAY_KEY_ID if payment.gateway == 'razorpay' else settings.STRIPE_PUBLISHABLE_KEY,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            currency_symbol=_currency_symbol(payment.currency),
            user_email=booking.user.email,
            user_phone=getattr(booking.user, 'phone_number', '') or '',
            user_name=booking.user.get_full_name() or booking.user.username,
            checkout_url=reverse('payment_verify'),
            invoice_url=reverse('payment_invoice', args=[payment.id]),
        )
        return context


class PaymentVerifyView(LoginRequiredMixin, View):
    """Step 6: verify Razorpay signature on the backend, then update state."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        payment_id = data.get('payment_id')
        gateway_data = data.get('gateway_data', {})
        declared_status = data.get('status', '')

        if not payment_id:
            return JsonResponse({'error': 'Missing payment_id'}, status=400)

        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        # Front-end reported the checkout failed/cancelled. The gateway data is
        # only recorded for diagnostics — the payment is marked failed locally
        # and the booking stays Pending so the user can retry.
        if declared_status == 'failed':
            from .services import _mark_failed
            try:
                if payment.status == Payment.Status.PENDING:
                    _mark_failed(payment, gateway_data.get('error') or 'Payment failed or cancelled at checkout')
                messages.error(request, 'Your payment was not completed. You can retry anytime.')
                return JsonResponse({
                    'status': 'failed',
                    'redirect_url': f"{reverse('payment_failed')}?payment={payment.id}",
                })
            except Exception as exc:
                return JsonResponse({'error': str(exc)}, status=500)

        try:
            payment = PaymentService.verify_payment(payment.id, gateway_data)
        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Payment not found'}, status=404)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)

        if payment.is_success:
            messages.success(
                request,
                f'Payment of {payment.currency} {payment.amount} received. '
                f'Booking {payment.booking.booking_id} is confirmed.',
            )
            return JsonResponse({
                'status': 'success',
                'redirect_url': f"{reverse('payment_success')}?payment={payment.id}",
            })

        messages.error(request, 'Payment could not be verified. Please retry.')
        return JsonResponse({
            'status': 'failed',
            'redirect_url': f"{reverse('payment_failed')}?payment={payment.id}",
        })


class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/payment_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_id = self.request.GET.get('payment')
        payment = get_object_or_404(Payment, id=payment_id, user=self.request.user)
        context['payment'] = payment
        context['booking'] = payment.booking
        context['currency_symbol'] = _currency_symbol(payment.currency)
        context['dashboard_url'] = reverse('dashboard')
        return context


class PaymentFailedView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/payment_failed.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_id = self.request.GET.get('payment')
        payment = get_object_or_404(Payment, id=payment_id, user=self.request.user)
        context['payment'] = payment
        context['booking'] = payment.booking
        context['currency_symbol'] = _currency_symbol(payment.currency)
        context['retry_url'] = f"{reverse('payment_checkout')}?booking={payment.booking.booking_id}"
        context['support_email'] = settings.SUPPORT_EMAIL
        return context


class PaymentHistoryView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'payments/payment_history.html'
    context_object_name = 'payments'
    paginate_by = 10

    def get_queryset(self):
        qs = Payment.objects.filter(user=self.request.user).select_related('booking')

        status = self.request.GET.get('status')
        gateway = self.request.GET.get('gateway')
        search = self.request.GET.get('search')

        if status:
            qs = qs.filter(status=status)
        if gateway:
            qs = qs.filter(gateway=gateway)
        if search:
            qs = qs.filter(
                Q(transaction_id__icontains=search) |
                Q(order_id__icontains=search) |
                Q(booking__booking_id__icontains=search)
            )
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PaymentFilterForm(self.request.GET or None)
        context['currency_symbol'] = _currency_symbol(
            getattr(settings, 'DEFAULT_CURRENCY', 'INR')
        )
        return context


class PaymentRetryView(LoginRequiredMixin, View):
    """Allow the user to retry a failed payment (creates a fresh attempt)."""

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        if payment.is_success:
            messages.info(request, 'This payment was already successful.')
            return redirect('payment_success')

        if payment.booking.payment_status == 'Paid':
            messages.info(request, 'This booking is already paid.')
            return redirect('booking_detail', payment.booking.booking_id)

        try:
            PaymentService.initiate_payment(payment.booking, payment.gateway)
            messages.success(request, 'Let’s try that again.')
        except Exception as exc:
            messages.error(request, f'Could not start a new payment attempt: {exc}')
        return redirect('payment_checkout')

    def get(self, request, payment_id):
        return self.post(request, payment_id)


class PaymentReconcileView(LoginRequiredMixin, View):
    """Re-sync a pending payment with the live Razorpay state (status check)."""

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)
        try:
            PaymentService.reconcile_payment(payment)
        except Exception as exc:
            messages.error(request, f'Could not check payment status: {exc}')
        if payment.is_success:
            messages.success(request, 'Your payment was confirmed successfully.')
            return redirect('payment_success')
        messages.info(request, 'Your payment is still pending at the gateway.')
        return redirect('payment_checkout')


class InvoiceDownloadView(LoginRequiredMixin, View):
    """Render the professional HTML invoice for a payment owned by the user."""

    def get(self, request, payment_id):
        from django.template.loader import render_to_string

        payment = get_object_or_404(
            Payment, id=payment_id, user=request.user
        )
        booking = payment.booking

        html = render_to_string('payments/invoice.html', {
            'payment': payment,
            'booking': booking,
            'invoice_no': payment.transaction_id,
            'invoice_date': payment.paid_at or payment.created_at,
            'SITE_NAME': settings.SITE_NAME,
            'SITE_URL': settings.SITE_URL,
            'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
            'SUPPORT_PHONE': settings.SUPPORT_PHONE,
            'currency_symbol': _currency_symbol(payment.currency),
            'billed_to': {
                'name': booking.contact_name or request.user.get_full_name(),
                'email': booking.contact_email or request.user.email,
                'phone': booking.contact_phone or getattr(request.user, 'phone_number', ''),
            },
            'item': {
                'label': booking.title_display,
                'destination': booking.destination_display,
                'dates': (
                    f'{booking.travel_start_date:%b %d, %Y} — '
                    f'{booking.travel_end_date:%b %d, %Y}'
                ),
                'travelers': booking.total_travelers,
            },
        }, request)

        response = HttpResponse(html, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="invoice-{payment.transaction_id}.html"'
        )
        return response


class PaymentAdminRefundView(UserPassesTestMixin, View):
    """Staff-only gateway refund (placeholder wired to the refund service).

    Refunds a successful payment through Razorpay and marks local state.
    """

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.is_staff)

    def handle_no_permission(self):
        return HttpResponse('Forbidden', status=403)

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        amount = _safe_int(request.POST.get('amount'))
        try:
            RazorpayService.refund_payment(payment, amount=amount)
            messages.success(
                request,
                f'Refund for {payment.transaction_id} processed successfully.',
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'Refund failed: {exc}')
        return redirect(request.META.get('HTTP_REFERER') or 'admin:payments_payment_changelist')


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(View):
    def post(self, request, gateway):
        if gateway not in ('razorpay', 'stripe'):
            return HttpResponse(status=400)

        try:
            event = PaymentService.process_webhook(gateway, request)
            if event:
                return JsonResponse({'status': 'processed'})
            return HttpResponse(status=400)
        except Exception:
            return HttpResponse(status=500)