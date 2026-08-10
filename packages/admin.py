from django.contrib import admin
from django.utils.html import format_html, mark_safe

from maps.utils import admin_map_preview_html

from .models import PackageImage, TravelPackage


class PackageImageInline(admin.TabularInline):
    model = PackageImage
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


@admin.register(TravelPackage)
class TravelPackageAdmin(admin.ModelAdmin):
    list_display = (
        'image_thumbnail', 'title', 'destination', 'country',
        'category_badge', 'duration_display',
        'price_display', 'discount_badge',
        'average_rating', 'featured_badge', 'status_badge',
    )
    list_display_links = ('image_thumbnail', 'title')
    list_filter = (
        'active', 'featured', 'category', 'destination', 'country',
        'difficulty_level', 'duration_days',
    )
    search_fields = (
        'title', 'destination', 'country', 'state',
        'description', 'best_travel_season',
    )
    ordering = ('-featured', '-average_rating', 'title')
    list_per_page = 25
    save_on_top = True
    date_hierarchy = 'created_at'
    actions = [
        'activate_packages', 'deactivate_packages',
        'mark_as_featured', 'unmark_as_featured',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'slug', 'cover_image',
                ('destination', 'country', 'state'),
                'category', 'description',
            )
        }),
        ('Destination Coordinates', {
            'fields': (
                ('latitude', 'longitude'),
            )
        }),
        ('Map Preview', {
            'fields': ('map_preview',),
            'classes': ('wide',),
        }),
        ('Duration & Difficulty', {
            'fields': (
                ('duration_days', 'duration_nights'),
                'difficulty_level', 'max_travelers',
            )
        }),
        ('Pricing', {
            'fields': (
                ('price', 'discount_percentage', 'discounted_price'),
            )
        }),
        ('Itinerary & Content', {
            'fields': (
                'itinerary', 'highlights',
                'inclusions', 'exclusions',
                'best_travel_season',
            ),
            'classes': ('wide',),
        }),
        ('Rating', {
            'fields': (
                ('average_rating', 'total_reviews'),
            )
        }),
        ('Status', {
            'fields': ('featured', 'active'),
        }),
    )

    readonly_fields = ('discounted_price', 'map_preview')

    @admin.display(description='Map Preview')
    def map_preview(self, obj):
        return admin_map_preview_html(obj.latitude, obj.longitude, title=obj.destination)

    def image_thumbnail(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:8px;object-fit:cover;" />',
                obj.cover_image.url
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:50px;height:50px;border-radius:8px;background:linear-gradient(135deg,'
            '#2563EB,#06B6D4);color:#fff;font-weight:700;font-size:16px;">{}</span>',
            obj.title[0].upper()
        )
    image_thumbnail.short_description = 'Image'

    def category_badge(self, obj):
        colors = {
            'Adventure': '#EF4444', 'Family': '#22C55E',
            'Honeymoon': '#EC4899', 'Luxury': '#F59E0B',
            'Solo': '#3B82F6', 'Group': '#8B5CF6',
            'Wildlife': '#10B981', 'Beach': '#06B6D4',
            'Hill Station': '#6366F1',
            'Wellness': '#14B8A6',
        }
        color = colors.get(obj.category, '#64748B')
        return format_html(
            '<span style="background:{}15;color:{};padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            color, color, obj.category
        )
    category_badge.short_description = 'Category'

    def duration_display(self, obj):
        return obj.duration_display
    duration_display.short_description = 'Duration'

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

    inlines = [PackageImageInline]

    @admin.action(description='Activate selected packages')
    def activate_packages(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} package(s) activated.')

    @admin.action(description='Deactivate selected packages')
    def deactivate_packages(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} package(s) deactivated.')

    @admin.action(description='Mark selected as Featured')
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} package(s) marked as featured.')

    @admin.action(description='Unmark selected Featured')
    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} package(s) unmarked as featured.')
