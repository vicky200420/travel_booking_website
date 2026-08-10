"""Notification & Communication — user-facing views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, TemplateView

from .models import Notification
from .services import NotificationService


class NotificationListView(LoginRequiredMixin, ListView):
    """Notification Center — search, filter by type, paginated."""

    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    TYPE_FILTERS = [c for c, _ in Notification.Type.choices]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        query = self.request.GET.get('q', '').strip()
        type_filter = self.request.GET.get('type', '').strip()
        read_filter = self.request.GET.get('read', '').strip()

        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(message__icontains=query)
            )
        if type_filter in self.TYPE_FILTERS:
            qs = qs.filter(type=type_filter)
        if read_filter in ('read', 'unread'):
            qs = qs.filter(is_read=(read_filter == 'read'))

        return qs.select_related('user')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_type'] = self.request.GET.get('type', '')
        context['active_read'] = self.request.GET.get('read', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['unread_total'] = NotificationService.unread_count(self.request.user)
        context['type_options'] = Notification.Type.choices
        context['current_url'] = self.request.get_full_path()
        return context


class NotificationDropdownView(LoginRequiredMixin, TemplateView):
    """Reusable dropdown fragment for the navbar bell (AJAX refresh)."""

    template_name = 'notifications/notification_dropdown.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_notifications'] = NotificationService.unread_count(self.request.user)
        context['recent_notifications'] = NotificationService.recent(self.request.user, 5)
        return context


class NotificationUnreadCountView(LoginRequiredMixin, View):
    """JSON endpoint for the animated bell badge."""

    def get(self, request):
        return JsonResponse({'count': NotificationService.unread_count(request.user)})


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, user=request.user
        )
        NotificationService.mark_read(notification)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'unread': NotificationService.unread_count(request.user),
            })
        if notification.action_url:
            return redirect(notification.action_url)
        return redirect('notifications:notification_center')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        updated = NotificationService.mark_all_read(request.user)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'updated': updated, 'unread': 0})
        return redirect('notifications:notification_center')


class NotificationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification, pk=pk, user=request.user
        )
        NotificationService.delete(notification)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'unread': NotificationService.unread_count(request.user),
            })
        return redirect('notifications:notification_center')
