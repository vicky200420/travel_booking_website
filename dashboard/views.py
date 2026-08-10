"""Dashboard — user travel hub + admin analytics views.

User pages are locked behind LoginRequiredMixin and only ever query the
authenticated user's own data (ownership is enforced in each queryset).

Admin analytics pages are locked behind :class:`AdminStaffRequiredMixin`
(staff members and superusers only, per Django's ``is_staff`` flag) and
expose read-only aggregates plus report exports.
"""
import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, TemplateView

from bookings.models import Booking
from notifications.models import Notification
from payments.models import Payment

from .forms import (
    DashboardPasswordForm,
    DashboardPictureForm,
    DashboardProfileForm,
    NotificationPreferencesForm,
    TravelPreferencesForm,
)
from .services import AdminAnalyticsService, DashboardService


class DashboardMixin(LoginRequiredMixin):
    """Shared context for the dashboard chrome (sidebar/topbar)."""

    active_page = 'dashboard'
    page_title = 'Dashboard'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_page'] = self.active_page
        context['page_title'] = self.page_title
        context['dash_membership'] = DashboardService.membership_level(user)
        context['dash_loyalty_points'] = DashboardService.loyalty_points(user)
        context['dash_profile'] = DashboardService.get_profile(user)
        return context


class DashboardView(DashboardMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'
    active_page = 'dashboard'
    page_title = 'Dashboard'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        labels, values = DashboardService.monthly_spend(user)
        context['dash_stats'] = DashboardService.stats(user)
        context['upcoming_bookings'] = DashboardService.upcoming_bookings(user)
        context['recent_notifications'] = DashboardService.notification_queryset(user)[:5]
        context['latest_payments'] = DashboardService.payment_queryset(user)[:4]
        context['spend_labels'] = labels
        context['spend_values'] = values
        return context


class DashboardBookingsView(DashboardMixin, ListView):
    template_name = 'dashboard/bookings.html'
    context_object_name = 'bookings'
    paginate_by = 8
    active_page = 'bookings'
    page_title = 'My Bookings'

    def get_queryset(self):
        qs = DashboardService.booking_queryset(self.request.user)
        query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        booking_type = self.request.GET.get('type', '').strip()
        if query:
            qs = qs.filter(
                Q(booking_id__icontains=query)
                | Q(contact_name__icontains=query)
                | Q(contact_email__icontains=query)
            )
        if status:
            qs = qs.filter(status=status)
        if booking_type:
            qs = qs.filter(booking_type=booking_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['active_status'] = self.request.GET.get('status', '')
        context['active_type'] = self.request.GET.get('type', '')
        context['status_options'] = Booking.Status.choices
        context['type_options'] = Booking.BookingType.choices
        context['query_string'] = _query_string(self.request, drop=['page'])
        return context


class DashboardPaymentsView(DashboardMixin, ListView):
    template_name = 'dashboard/payments.html'
    context_object_name = 'payments'
    paginate_by = 10
    active_page = 'payments'
    page_title = 'Payments'

    def get_queryset(self):
        qs = DashboardService.payment_queryset(self.request.user)
        query = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()
        if query:
            qs = qs.filter(
                Q(transaction_id__icontains=query)
                | Q(booking__booking_id__icontains=query)
            )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['active_status'] = self.request.GET.get('status', '')
        context['status_options'] = Payment.Status.choices
        context['query_string'] = _query_string(self.request, drop=['page'])
        return context


class DashboardInvoiceView(DashboardMixin, View):
    """Printable HTML invoice for a payment owned by the user."""

    active_page = 'payments'
    page_title = 'Payments'

    def get(self, request, payment_id):
        payment = get_object_or_404(
            Payment, id=payment_id, user=request.user
        )
        booking = payment.booking
        response = self._render_invoice(request, payment, booking)
        response['Content-Disposition'] = (
            f'attachment; filename="invoice-{payment.transaction_id}.html"'
        )
        return response

    def _render_invoice(self, request, payment, booking):
        from django.conf import settings
        from django.template.loader import render_to_string
        html = render_to_string('dashboard/invoice.html', {
            'payment': payment,
            'booking': booking,
            'invoice_no': payment.transaction_id,
            'invoice_date': payment.paid_at or payment.created_at,
            'SITE_NAME': settings.SITE_NAME,
            'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
            'billed_to': {
                'name': booking.contact_name or request.user.get_full_name(),
                'email': booking.contact_email or request.user.email,
                'phone': booking.contact_phone or request.user.phone_number or '',
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
        from django.http import HttpResponse
        return HttpResponse(html, content_type='text/html')


class DashboardWishlistView(DashboardMixin, ListView):
    template_name = 'dashboard/wishlist.html'
    context_object_name = 'wishlist_items'
    paginate_by = 12
    active_page = 'wishlist'
    page_title = 'My Wishlist'

    def get_queryset(self):
        return DashboardService.wishlist_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wishlist_total'] = self.get_queryset().count()
        return context


class WishlistToggleView(LoginRequiredMixin, View):
    """AJAX add/remove of a hotel / flight / package to the user's wishlist."""

    def post(self, request):
        model_key = request.POST.get('model', '')
        object_id = request.POST.get('object_id', '')
        if not object_id.isdigit():
            return JsonResponse({'ok': False, 'error': 'Invalid item.'}, status=400)
        try:
            action, item = DashboardService.toggle_wishlist(
                request.user, model_key, int(object_id)
            )
        except ValidationError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
        return JsonResponse({'ok': True, 'action': action, 'in_wishlist': action == 'added'})


class WishlistRemoveView(LoginRequiredMixin, View):
    def post(self, request, item_id):
        removed = DashboardService.remove_wishlist(request.user, item_id)
        if removed:
            messages.success(request, 'Item removed from your wishlist.')
        return redirect('dashboard_wishlist')


class DashboardReviewsView(DashboardMixin, ListView):
    template_name = 'dashboard/reviews.html'
    context_object_name = 'reviews'
    paginate_by = 8
    active_page = 'reviews'
    page_title = 'My Reviews'

    def get_queryset(self):
        return DashboardService.review_queryset(self.request.user)


class DashboardNotificationsView(DashboardMixin, ListView):
    template_name = 'dashboard/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 10
    active_page = 'notifications'
    page_title = 'Notifications'

    TYPE_FILTERS = [c for c, _ in Notification.Type.choices]

    def get_queryset(self):
        qs = DashboardService.notification_queryset(self.request.user)
        type_filter = self.request.GET.get('type', '').strip()
        read_filter = self.request.GET.get('read', '').strip()
        if type_filter in self.TYPE_FILTERS:
            qs = qs.filter(type=type_filter)
        if read_filter in ('read', 'unread'):
            qs = qs.filter(is_read=(read_filter == 'read'))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_type'] = self.request.GET.get('type', '')
        context['active_read'] = self.request.GET.get('read', '')
        context['unread_total'] = DashboardService.notification_queryset(
            self.request.user
        ).filter(is_read=False).count()
        context['type_options'] = Notification.Type.choices
        context['query_string'] = _query_string(self.request, drop=['page'])
        return context


class DashboardSettingsView(DashboardMixin, TemplateView):
    template_name = 'dashboard/settings.html'
    active_page = 'settings'
    page_title = 'Settings'

    # --------------------------------------------------------------- GET

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = DashboardService.get_profile(user)
        context['tab'] = self.request.GET.get('tab', 'profile')
        context['profile_form'] = DashboardProfileForm(instance=user)
        context['picture_form'] = DashboardPictureForm(instance=user)
        context['password_form'] = DashboardPasswordForm()
        context['travel_form'] = TravelPreferencesForm.from_profile(profile)
        context['notif_form'] = NotificationPreferencesForm.from_profile(profile)
        return context

    # -------------------------------------------------------------- POST

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        user = request.user
        handlers = {
            'profile': self._handle_profile,
            'picture': self._handle_picture,
            'password': self._handle_password,
            'travel_preferences': self._handle_travel,
            'notification_preferences': self._handle_notifications,
        }
        handler = handlers.get(action)
        if not handler:
            messages.error(request, 'Unknown settings action.')
            return redirect(self._tab_url('profile'))
        return handler(request, user)

    def _tab_url(self, tab):
        return f'{reverse("dashboard_settings")}?tab={tab}'

    def _handle_profile(self, request, user):
        form = DashboardProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile information updated.')
            return redirect(self._tab_url('profile'))
        context = self.get_context_data()
        context.update(tab='profile', profile_form=form)
        return self.render_to_response(context)

    def _handle_picture(self, request, user):
        form = DashboardPictureForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile picture updated.')
            return redirect(self._tab_url('picture'))
        context = self.get_context_data()
        context.update(tab='picture', picture_form=form)
        return self.render_to_response(context)

    def _handle_password(self, request, user):
        form = DashboardPasswordForm(request.POST)
        if form.is_valid():
            try:
                DashboardService.change_password(
                    user,
                    form.cleaned_data['current_password'],
                    form.cleaned_data['new_password'],
                )
            except ValidationError as exc:
                for msg in exc.messages:
                    form.add_error('current_password', msg)
            else:
                messages.success(
                    request, 'Password changed. Use it on your next login.'
                )
                return redirect(self._tab_url('password'))
        context = self.get_context_data()
        context.update(tab='password', password_form=form)
        return self.render_to_response(context)

    def _handle_travel(self, request, user):
        form = TravelPreferencesForm(request.POST)
        if form.is_valid():
            DashboardService.update_travel_preferences(user, request.POST)
            messages.success(request, 'Travel preferences saved.')
            return redirect(self._tab_url('travel'))
        context = self.get_context_data()
        context.update(tab='travel', travel_form=form)
        return self.render_to_response(context)

    def _handle_notifications(self, request, user):
        form = NotificationPreferencesForm(request.POST)
        if form.is_valid():
            DashboardService.update_notification_preferences(user, request.POST)
            messages.success(request, 'Notification preferences saved.')
            return redirect(self._tab_url('notifications'))
        context = self.get_context_data()
        context.update(tab='notifications', notif_form=form)
        return self.render_to_response(context)


class AdminStaffRequiredMixin(UserPassesTestMixin):
    """Restrict a view to authenticated staff / superuser accounts.

    ``is_staff`` is the Django-native flag that also covers superusers, so
    this is the single security gate for every admin analytics endpoint.

    Anonymous visitors are redirected to the login page; authenticated
    non-staff users get a 403.
    """

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.is_staff)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class AdminDashboardView(AdminStaffRequiredMixin, TemplateView):
    """Executive analytics dashboard (staff only).

    ``?json=1`` returns the same payload as JSON so the front-end can
    auto-refresh charts and counters without a full page reload.
    """

    template_name = 'dashboard/admin_dashboard.html'
    active_page = 'admin_analytics'
    page_title = 'Admin Analytics'

    def get(self, request, *args, **kwargs):
        if request.GET.get('json') == '1':
            window = AdminAnalyticsService.parse_range(request.GET)
            return JsonResponse(
                {
                    'kpis': AdminAnalyticsService.kpi_cards(window),
                    'charts': AdminAnalyticsService.charts(window),
                    'window': window,
                },
                json_dumps_params={'default': str},
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        window = AdminAnalyticsService.parse_range(self.request.GET)
        context['analytics_window'] = window
        context['analytics_kpis'] = AdminAnalyticsService.kpi_cards(window)
        context['analytics_charts'] = AdminAnalyticsService.charts(window)
        context['analytics_activity'] = AdminAnalyticsService.activity()
        context['analytics_json'] = json.dumps(
            {
                'window': window,
                'charts': AdminAnalyticsService.charts(window),
                'urls': {
                    'search': reverse('admin_analytics_search'),
                    'export_pdf': reverse('admin_report_export', args=['revenue', 'pdf']),
                },
            },
            default=str,
        )
        context['analytics_qs'] = _query_string(self.request)
        return context


class AdminAnalyticsSearchView(AdminStaffRequiredMixin, View):
    """JSON search across bookings, users, payments and destinations."""

    def get(self, request):
        results = AdminAnalyticsService.search(request.GET.get('q', ''))
        return JsonResponse(results)


class AdminReportExportView(AdminStaffRequiredMixin, View):
    """CSV / XLSX / PDF export of a scoped report (staff only)."""

    VALID_REPORTS = ('revenue', 'bookings', 'payments', 'users')
    VALID_FORMATS = ('csv', 'xlsx', 'pdf')

    def get(self, request, report, fmt):
        report = report.lower()
        fmt = fmt.lower()
        if report not in self.VALID_REPORTS or fmt not in self.VALID_FORMATS:
            raise Http404('Unknown report or format.')
        window = AdminAnalyticsService.parse_range(request.GET)
        return AdminAnalyticsService.export(report, fmt, window)


def _query_string(request, drop=None):
    """Re-serialise current GET params (minus ``drop``) for pagination links."""
    drop = drop or []
    params = [(k, v) for k, v in request.GET.items() if k not in drop]
    from urllib.parse import urlencode
    return urlencode(params)
