from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Flight


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = (
        'airline_logo_thumbnail', 'airline_name', 'flight_number',
        'departure_city', 'destination_city',
        'departure_date', 'departure_time',
        'available_seats', 'total_seats',
        'price_display', 'discount_badge', 'status_colored', 'refundable_icon'
    )
    list_display_links = ('airline_logo_thumbnail', 'flight_number')
    list_filter = (
        'airline_name', 'departure_city', 'destination_city',
        'status', 'cabin_class', 'refundable', 'flight_type'
    )
    search_fields = (
        'flight_number', 'airline_name',
        'departure_city', 'destination_city',
        'departure_airport', 'arrival_airport'
    )
    ordering = ('-departure_date', 'departure_time')
    date_hierarchy = 'departure_date'
    list_per_page = 25
    list_select_related = True
    save_on_top = True
    actions = ['mark_as_scheduled', 'mark_as_delayed', 'mark_as_cancelled', 'mark_as_completed']

    fieldsets = (
        ('Route Information', {
            'fields': (
                'airline_name', 'airline_logo', 'flight_number',
                ('departure_airport', 'arrival_airport'),
                ('departure_city', 'destination_city'),
            )
        }),
        ('Schedule', {
            'fields': (
                ('departure_date', 'departure_time'),
                ('arrival_date', 'arrival_time'),
                'flight_duration',
            )
        }),
        ('Class & Pricing', {
            'fields': (
                'flight_type', 'cabin_class',
                ('price', 'discount_percentage', 'discounted_price'),
            )
        }),
        ('Capacity', {
            'fields': (('total_seats', 'available_seats'),)
        }),
        ('Rules & Status', {
            'fields': (
                'baggage_allowance', 'refundable',
                'status', 'description',
            )
        }),
    )

    readonly_fields = ('discounted_price',)

    def airline_logo_thumbnail(self, obj):
        if obj.airline_logo:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:8px;object-fit:cover;" />',
                obj.airline_logo.url
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:40px;height:40px;border-radius:8px;background:#2563EB;color:#fff;'
            'font-weight:600;font-size:14px;">{}</span>',
            obj.airline_name[0].upper()
        )
    airline_logo_thumbnail.short_description = 'Logo'

    def price_display(self, obj):
        if obj.has_discount():
            return format_html(
                '<span style="text-decoration:line-through;color:#94a3b8;">${}</span> '
                '<span style="color:#22c55e;font-weight:700;">${}</span>',
                obj.price, obj.discounted_price
            )
        return format_html(
            '<span style="font-weight:600;">${}</span>', obj.price
        )
    price_display.short_description = 'Price'

    def discount_badge(self, obj):
        if obj.has_discount():
            return format_html(
                '<span style="background:#22c55e;color:white;padding:2px 8px;border-radius:6px;font-size:11px;">{}% OFF</span>',
                obj.discount_percentage
            )
        return "-"
    discount_badge.short_description = 'Discount'

    def status_colored(self, obj):
        colors = {
            'scheduled': '#2563EB',
            'delayed': '#F59E0B',
            'cancelled': '#EF4444',
            'completed': '#22C55E',
        }
        return format_html(
            '<span style="background:{}10;color:{};padding:4px 12px;'
            'border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            colors.get(obj.status, '#64748B'),
            colors.get(obj.status, '#64748B'),
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def refundable_icon(self, obj):
        if obj.refundable:
            return mark_safe('<span style="color:#22c55e;">&#10003;</span>')
        return mark_safe('<span style="color:#EF4444;">&#10007;</span>')
    refundable_icon.short_description = 'Refundable'

    @admin.action(description='Mark selected flights as Scheduled')
    def mark_as_scheduled(self, request, queryset):
        updated = queryset.update(status='scheduled')
        self.message_user(request, f'{updated} flight(s) marked as Scheduled.')

    @admin.action(description='Mark selected flights as Delayed')
    def mark_as_delayed(self, request, queryset):
        updated = queryset.update(status='delayed')
        self.message_user(request, f'{updated} flight(s) marked as Delayed.')

    @admin.action(description='Mark selected flights as Cancelled')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} flight(s) marked as Cancelled.')

    @admin.action(description='Mark selected flights as Completed')
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} flight(s) marked as Completed.')
