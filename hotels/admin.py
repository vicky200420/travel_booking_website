from django.contrib import admin
from django.utils.html import format_html, mark_safe

from maps.utils import admin_map_preview_html

from .models import Hotel, HotelImage


class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 3
    fields = ('image', 'caption', 'is_primary', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" width="80" height="60" style="border-radius:6px;object-fit:cover;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = 'Preview'


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        'image_thumbnail', 'name', 'city', 'country',
        'star_rating_display', 'average_rating',
        'price_display', 'discount_badge',
        'available_rooms', 'featured_badge', 'status_badge',
    )
    list_display_links = ('image_thumbnail', 'name')
    list_filter = (
        'active', 'featured', 'star_rating', 'city', 'country',
        'wifi', 'pool', 'parking', 'spa', 'gym',
        'restaurant', 'ac', 'breakfast', 'pet_friendly',
    )
    search_fields = (
        'name', 'city', 'state', 'country',
        'address', 'contact_email', 'contact_phone',
    )
    ordering = ('-featured', '-average_rating', 'name')
    list_per_page = 25
    save_on_top = True
    date_hierarchy = 'created_at'
    actions = ['activate_hotels', 'deactivate_hotels', 'mark_as_featured', 'unmark_as_featured']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'slug', 'image',
                ('city', 'state', 'country'),
                'address', 'description',
            )
        }),
        ('Rating & Pricing', {
            'fields': (
                ('star_rating', 'average_rating'),
                ('price_per_night', 'discount_percentage', 'discounted_price'),
            )
        }),
        ('Room Details', {
            'fields': (
                ('total_rooms', 'available_rooms'),
                ('check_in_time', 'check_out_time'),
            )
        }),
        ('Amenities', {
            'fields': (
                ('wifi', 'pool', 'parking'),
                ('spa', 'gym', 'restaurant'),
                ('ac', 'breakfast', 'pet_friendly'),
            )
        }),
        ('Location & Contact', {
            'fields': (
                ('latitude', 'longitude'),
                ('contact_email', 'contact_phone'),
                'website',
            )
        }),
        ('Map Preview', {
            'fields': ('map_preview',),
            'classes': ('wide',),
        }),
        ('Status', {
            'fields': ('featured', 'active'),
        }),
    )

    readonly_fields = ('discounted_price', 'map_preview')

    @admin.display(description='Map Preview')
    def map_preview(self, obj):
        return admin_map_preview_html(obj.latitude, obj.longitude, title=obj.name)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:8px;object-fit:cover;" />',
                obj.image.url
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:50px;height:50px;border-radius:8px;background:linear-gradient(135deg,'
            '#2563EB,#06B6D4);color:#fff;font-weight:700;font-size:16px;">{}</span>',
            obj.name[0].upper()
        )
    image_thumbnail.short_description = 'Image'

    def star_rating_display(self, obj):
        stars = '★' * obj.star_rating + '☆' * (5 - obj.star_rating)
        color = '#F59E0B'
        return format_html(
            '<span style="color:{};font-size:14px;letter-spacing:1px;">{}</span>',
            color, stars
        )
    star_rating_display.short_description = 'Rating'

    def price_display(self, obj):
        if obj.has_discount():
            return format_html(
                '<span style="text-decoration:line-through;color:#94a3b8;">${}</span> '
                '<span style="color:#22c55e;font-weight:700;">${}</span>',
                obj.price_per_night, obj.discounted_price
            )
        return format_html(
            '<span style="font-weight:600;">${}</span>', obj.price_per_night
        )
    price_display.short_description = 'Price'

    def discount_badge(self, obj):
        if obj.has_discount():
            return format_html(
                '<span style="background:#22c55e;color:white;padding:2px 8px;'
                'border-radius:6px;font-size:11px;font-weight:600;">{}% OFF</span>',
                obj.discount_percentage
            )
        return "-"
    discount_badge.short_description = 'Discount'

    def featured_badge(self, obj):
        if obj.featured:
            return mark_safe(
                '<span style="color:#F59E0B;font-size:16px;">&#9733;</span>'
            )
        return mark_safe('<span style="color:#e2e8f0;font-size:16px;">&#9733;</span>')
    featured_badge.short_description = 'Featured'

    def status_badge(self, obj):
        if obj.active:
            return mark_safe(
                '<span style="background:#22c55e10;color:#22c55e;padding:4px 12px;'
                'border-radius:20px;font-size:12px;font-weight:600;">Active</span>'
            )
        return mark_safe(
            '<span style="background:#ef444410;color:#ef4444;padding:4px 12px;'
            'border-radius:20px;font-size:12px;font-weight:600;">Inactive</span>'
        )
    status_badge.short_description = 'Status'

    inlines = [HotelImageInline]

    @admin.action(description='Activate selected hotels')
    def activate_hotels(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} hotel(s) activated.')

    @admin.action(description='Deactivate selected hotels')
    def deactivate_hotels(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} hotel(s) deactivated.')

    @admin.action(description='Mark selected as Featured')
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} hotel(s) marked as featured.')

    @admin.action(description='Unmark selected Featured')
    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} hotel(s) unmarked as featured.')
