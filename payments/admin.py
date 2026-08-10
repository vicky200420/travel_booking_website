from django.contrib import admin
from django.utils.html import format_html

from .models import Payment
from .services import RazorpayService


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id_link', 'booking_link', 'user_info',
        'gateway_badge', 'amount_display', 'currency_display',
        'status_badge', 'payment_id_short', 'order_id_short',
        'payment_method_display', 'paid',
    )
    list_display_links = ('transaction_id_link',)
    list_filter = ('status', 'gateway', 'currency', 'payment_method')
    search_fields = (
        'transaction_id', 'order_id', 'payment_id', 'refund_id',
        'user__username', 'user__email', 'booking__booking_id',
    )
    ordering = ('-created_at',)
    list_per_page = 25
    save_on_top = True
    date_hierarchy = 'created_at'
    actions = ['refund_selected', 'mark_as_refunded', 'mark_as_success']

    fieldsets = (
        ('Transaction Info', {
            'fields': (
                'transaction_id', 'order_id', 'payment_id', 'refund_id',
                'gateway', ('amount', 'currency'),
            ),
        }),
        ('Booking & User', {
            'fields': ('booking', 'user'),
        }),
        ('Status', {
            'fields': ('status', 'payment_method', 'paid_at', 'refunded_at'),
        }),
        ('Gateway Response', {
            'fields': ('gateway_response',),
            'classes': ('wide',),
        }),
    )

    readonly_fields = (
        'transaction_id', 'order_id', 'payment_id', 'refund_id',
        'amount', 'currency', 'gateway_response', 'paid_at',
        'refunded_at', 'created_at', 'updated_at',
    )

    def transaction_id_link(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-weight:600;font-size:0.85rem;">{}</span>',
            obj.transaction_id
        )
    transaction_id_link.short_description = 'Transaction'

    def booking_link(self, obj):
        return format_html(
            '<span style="font-family:monospace;">{}</span>',
            obj.booking.booking_id
        )
    booking_link.short_description = 'Booking'

    def user_info(self, obj):
        return format_html(
            '<span style="font-weight:600;">{}</span>',
            obj.user.username
        )
    user_info.short_description = 'User'

    def gateway_badge(self, obj):
        colors = {'razorpay': '#2563EB', 'stripe': '#8B5CF6'}
        color = colors.get(obj.gateway, '#64748B')
        return format_html(
            '<span style="background:{}15;color:{};padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            color, color, obj.get_gateway_display()
        )
    gateway_badge.short_description = 'Gateway'

    def amount_display(self, obj):
        return format_html(
            '<span style="font-weight:700;">{}</span>',
            obj.amount
        )
    amount_display.short_description = 'Amount'

    def currency_display(self, obj):
        return obj.currency
    currency_display.short_description = 'Currency'

    def status_badge(self, obj):
        colors = {
            'Pending': ('#F59E0B', '#F59E0B'),
            'Success': ('#22C55E', '#22C55E'),
            'Failed': ('#EF4444', '#EF4444'),
            'Refunded': ('#8B5CF6', '#8B5CF6'),
        }
        bg, text = colors.get(obj.status, ('#64748B', '#64748B'))
        return format_html(
            '<span style="background:{}15;color:{};padding:4px 12px;'
            'border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            bg, text, obj.status
        )
    status_badge.short_description = 'Status'

    def payment_id_short(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:11px;color:#334155;">{}</span>',
            obj.payment_id or '-'
        )
    payment_id_short.short_description = 'Payment ID'

    def order_id_short(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-size:11px;color:#64748B;">{}</span>',
            obj.order_id or '-'
        )
    order_id_short.short_description = 'Order ID'

    def payment_method_display(self, obj):
        return obj.payment_method or '-'
    payment_method_display.short_description = 'Method'

    def paid(self, obj):
        if obj.paid_at:
            return format_html(
                '<span style="font-size:11px;color:#64748B;">{}</span>',
                obj.paid_at.strftime('%d %b %Y %H:%M')
            )
        return '-'
    paid.short_description = 'Paid At'

    @admin.action(description='Refund selected via gateway')
    def refund_selected(self, request, queryset):
        refunded = 0
        for payment in queryset.filter(status='Success'):
            try:
                RazorpayService.refund_payment(payment)
                refunded += 1
            except Exception as exc:
                self.message_user(request, f'Refund failed for {payment}: {exc}', level='error')
        self.message_user(request, f'{refunded} payment(s) refunded via gateway.')

    @admin.action(description='Mark selected as Refunded (local only)')
    def mark_as_refunded(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='Success').update(
            status='Refunded', refunded_at=timezone.now()
        )
        self.message_user(request, f'{updated} payment(s) marked as refunded.')

    @admin.action(description='Mark selected as Success')
    def mark_as_success(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='Pending').update(
            status='Success', paid_at=timezone.now()
        )
        self.message_user(request, f'{updated} payment(s) marked as success.')