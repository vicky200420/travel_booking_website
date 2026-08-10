from django.contrib import admin
from django.utils.html import format_html

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_id_link', 'user_info', 'booking_type_badge',
        'destination', 'travel_dates', 'status_badge',
        'payment_badge', 'grand_total_display', 'created',
    )
    list_display_links = ('booking_id_link',)
    list_filter = (
        'status', 'payment_status', 'booking_type',
        'travel_start_date', 'booking_date',
    )
    search_fields = (
        'booking_id', 'user__username', 'user__email',
        'contact_name', 'contact_email', 'contact_phone',
    )
    ordering = ('-created_at',)
    list_per_page = 25
    save_on_top = True
    date_hierarchy = 'booking_date'
    actions = [
        'confirm_bookings', 'cancel_bookings',
        'complete_bookings', 'refund_bookings',
    ]

    fieldsets = (
        ('Booking Reference', {
            'fields': ('booking_id', 'user', 'booking_type', 'booking_date'),
        }),
        ('Booking Details', {
            'fields': (
                ('flight', 'hotel', 'package'),
                ('travel_start_date', 'travel_end_date'),
            ),
        }),
        ('Travelers', {
            'fields': (
                ('adults', 'children', 'infants'),
                'total_travelers',
            ),
        }),
        ('Contact Information', {
            'fields': (
                'contact_name', 'contact_email', 'contact_phone',
                'special_requests',
            ),
        }),
        ('Pricing', {
            'fields': (
                ('base_price', 'discount'),
                ('taxes', 'service_fee'),
                'grand_total',
            ),
        }),
        ('Status', {
            'fields': (
                ('status', 'payment_status'),
            ),
        }),
    )

    readonly_fields = (
        'booking_id', 'booking_date', 'total_travelers',
        'base_price', 'taxes', 'discount', 'service_fee',
        'grand_total', 'created_at', 'updated_at',
    )

    def booking_id_link(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-weight:700;">{}</span>',
            obj.booking_id
        )
    booking_id_link.short_description = 'Booking ID'

    def user_info(self, obj):
        return format_html(
            '<div><span style="font-weight:600;">{}</span><br>'
            '<span style="font-size:11px;color:#64748B;">{}</span></div>',
            obj.user.username, obj.contact_email
        )
    user_info.short_description = 'User'

    def booking_type_badge(self, obj):
        colors = {'Flight': '#3B82F6', 'Hotel': '#8B5CF6', 'Package': '#10B981'}
        color = colors.get(obj.booking_type, '#64748B')
        return format_html(
            '<span style="background:{}15;color:{};padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            color, color, obj.booking_type
        )
    booking_type_badge.short_description = 'Type'

    def destination(self, obj):
        return obj.destination_display
    destination.short_description = 'Destination'

    def travel_dates(self, obj):
        return format_html(
            '<span style="font-size:12px;">{} — {}</span>',
            obj.travel_start_date, obj.travel_end_date
        )
    travel_dates.short_description = 'Travel Dates'

    def grand_total_display(self, obj):
        return format_html(
            '<span style="font-weight:700;color:#2563EB;">${}</span>',
            obj.grand_total
        )
    grand_total_display.short_description = 'Total'

    def created(self, obj):
        return format_html(
            '<span style="font-size:11px;color:#64748B;">{}</span>',
            obj.created_at.strftime('%d %b %Y')
        )
    created.short_description = 'Created'

    def status_badge(self, obj):
        colors = {
            'Pending': ('#F59E0B', '#F59E0B'),
            'Confirmed': ('#22C55E', '#22C55E'),
            'Cancelled': ('#EF4444', '#EF4444'),
            'Completed': ('#3B82F6', '#3B82F6'),
            'Refunded': ('#64748B', '#64748B'),
        }
        bg, text = colors.get(obj.status, ('#64748B', '#64748B'))
        return format_html(
            '<span style="background:{}15;color:{};padding:4px 12px;'
            'border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            bg, text, obj.status
        )
    status_badge.short_description = 'Status'

    def payment_badge(self, obj):
        colors = {
            'Pending': ('#F59E0B', '#F59E0B'),
            'Paid': ('#22C55E', '#22C55E'),
            'Failed': ('#EF4444', '#EF4444'),
            'Refunded': ('#8B5CF6', '#8B5CF6'),
        }
        bg, text = colors.get(obj.payment_status, ('#64748B', '#64748B'))
        return format_html(
            '<span style="background:{}15;color:{};padding:4px 12px;'
            'border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            bg, text, obj.payment_status
        )
    payment_badge.short_description = 'Payment'

    @admin.action(description='Confirm selected bookings')
    def confirm_bookings(self, request, queryset):
        updated = queryset.exclude(status__in=['Cancelled', 'Refunded', 'Completed']).update(
            status=Booking.Status.CONFIRMED, payment_status=Booking.PaymentStatus.PAID
        )
        self.message_user(request, f'{updated} booking(s) confirmed.')

    @admin.action(description='Cancel selected bookings')
    def cancel_bookings(self, request, queryset):
        from .services import BookingService
        count = 0
        for booking in queryset:
            try:
                BookingService.cancel_booking(booking)
                count += 1
            except Exception:
                pass
        self.message_user(request, f'{count} booking(s) cancelled.')

    @admin.action(description='Complete selected bookings')
    def complete_bookings(self, request, queryset):
        updated = queryset.filter(status='Confirmed').update(status=Booking.Status.COMPLETED)
        self.message_user(request, f'{updated} booking(s) marked as completed.')

    @admin.action(description='Refund selected bookings')
    def refund_bookings(self, request, queryset):
        updated = queryset.filter(status='Cancelled').update(
            status=Booking.Status.REFUNDED, payment_status=Booking.PaymentStatus.REFUNDED
        )
        self.message_user(request, f'{updated} booking(s) refunded.')
