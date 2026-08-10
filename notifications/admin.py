"""Notification & Communication — admin panel."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Notification
from .services import NotificationService

User = get_user_model()


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user_link', 'type_badge', 'audience_badge',
        'read_state', 'broadcast_state', 'created',
    )
    list_filter = ('type', 'audience', 'is_read', 'is_broadcast')
    search_fields = ('title', 'message', 'user__username', 'user__email')
    ordering = ('-created_at',)
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']

    fieldsets = (
        ('Notification', {
            'fields': ('user', 'title', 'message', 'type', 'icon'),
        }),
        ('Delivery', {
            'fields': (
                ('action_url', 'is_read', 'read_at'),
                ('is_broadcast', 'audience', 'created_at'),
            ),
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('wide',),
        }),
    )

    readonly_fields = ('created_at',)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('broadcast/', self.admin_site.admin_view(self.broadcast_view), name='notification-broadcast'),
        ]
        return custom + urls

    # ------------------------------------------------------------ columns

    def user_link(self, obj):
        return format_html(
            '<span style="font-weight:600;">{}</span><br>'
            '<span style="font-size:11px;color:#64748B;">{}</span>',
            obj.user.username, obj.user.email
        )
    user_link.short_description = 'User'

    def type_badge(self, obj):
        colors = Notification.TYPE_COLORS
        color = colors.get(obj.type, '#64748B')
        return format_html(
            '<span style="background:{}15;color:{};padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            color, color, obj.get_type_display()
        )
    type_badge.short_description = 'Type'

    def audience_badge(self, obj):
        if obj.audience == Notification.Audience.ALL:
            return format_html('<span style="color:#64748B;">Everyone</span>')
        return obj.get_audience_display()
    audience_badge.short_description = 'Audience'

    def read_state(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color:#22C55E;font-weight:600;">Read</span>'
                '<br><span style="font-size:11px;color:#94A3B8;">{}</span>',
                obj.read_at.strftime('%d %b %H:%M') if obj.read_at else '-'
            )
        return format_html('<span style="color:#2563EB;font-weight:700;">Unread</span>')
    read_state.short_description = 'State'

    def broadcast_state(self, obj):
        return '✓' if obj.is_broadcast else '—'
    broadcast_state.short_description = 'Broadcast'

    def created(self, obj):
        return format_html(
            '<span style="font-size:11px;color:#64748B;">{}</span>',
            obj.created_at.strftime('%d %b %Y %H:%M')
        )
    created.short_description = 'Created'

    # ------------------------------------------------------------- actions

    @admin.action(description='Mark selected as read')
    def mark_as_read(self, request, queryset):
        updated = queryset.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        self.message_user(request, f'{updated} notification(s) marked as read.')

    @admin.action(description='Mark selected as unread')
    def mark_as_unread(self, request, queryset):
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notification(s) marked as unread.')

    # ------------------------------------------------------------ broadcast

    def broadcast_view(self, request):
        """Admin page to fan a notification (and optionally email) out to users."""
        from django import forms

        class BroadcastForm(forms.Form):
            title = forms.CharField(max_length=200)
            message = forms.CharField(widget=forms.Textarea, required=False)
            type = forms.ChoiceField(
                choices=Notification.Type.choices,
                initial=Notification.Type.PROMOTION,
            )
            audience = forms.ChoiceField(
                choices=Notification.Audience.choices,
                initial=Notification.Audience.ALL,
            )
            action_url = forms.CharField(max_length=500, required=False)
            icon = forms.CharField(max_length=50, required=False)

        form = BroadcastForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            cd = form.cleaned_data
            count = NotificationService.broadcast(
                title=cd['title'],
                message=cd['message'],
                type=cd['type'],
                action_url=cd['action_url'],
                icon=cd['icon'],
                audience=cd['audience'],
            )
            self.message_user(request, f'Notification sent to {count} user(s).')
            return redirect(reverse('admin:notifications_notification_changelist'))

        context = {
            **self.admin_site.each_context(request),
            'title': 'Broadcast notification',
            'form': form,
            'opts': self.model._meta,
            'media': self.media,
            'app_label': self.model._meta.app_label,
            'change': False,
            'is_popup': False,
            'save_as': False,
            'has_delete_permission': False,
            'has_add_permission': True,
            'has_change_permission': True,
            'has_view_permission': True,
            'show_delete': False,
        }
        return TemplateResponse(request, 'admin/broadcast_form.html', context)
