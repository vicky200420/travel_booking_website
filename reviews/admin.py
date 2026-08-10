from django.contrib import admin
from django.utils.html import format_html

from .models import Review, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:60px;object-fit:cover;border-radius:6px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'review_preview', 'rating_stars', 'user_link', 'item_link',
        'content_type_badge', 'verified_badge', 'approved_badge',
        'helpful_display', 'created_display',
    ]
    list_display_links = ['review_preview']
    list_filter = [
        'rating', 'is_approved', 'is_verified_booking',
        'created_at', 'hotel', 'package',
    ]
    search_fields = [
        'title', 'review_text', 'user__username', 'user__email',
        'hotel__name', 'package__title',
    ]
    list_per_page = 25
    save_on_top = True
    date_hierarchy = 'created_at'
    inlines = [ReviewImageInline]
    actions = ['approve_reviews', 'hide_reviews', 'delete_selected']

    fieldsets = (
        ('Review', {
            'fields': ('rating', 'title', 'review_text'),
        }),
        ('User & Booking', {
            'fields': ('user', 'booking', 'hotel', 'package'),
        }),
        ('Status', {
            'fields': ('is_approved', 'is_verified_booking', 'helpful_count'),
        }),
    )

    readonly_fields = ['is_verified_booking', 'helpful_count', 'created_at', 'updated_at']

    def review_preview(self, obj):
        return format_html(
            '<div style="max-width:280px;"><strong style="font-size:13px;">{}</strong>'
            '<br><span style="font-size:11px;color:#64748B;">{}</span></div>',
            obj.title[:60], obj.review_text[:100]
        )
    review_preview.short_description = 'Review'

    def rating_stars(self, obj):
        filled = '★' * obj.rating
        empty = '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color:#F59E0B;font-size:14px;letter-spacing:2px;">{}{}</span>',
            filled, empty
        )
    rating_stars.short_description = 'Rating'

    def user_link(self, obj):
        return format_html(
            '<a href="{}admin/accounts/customuser/{}/change/" target="_blank" '
            'style="font-weight:600;">{}</a>',
            obj.user.id, obj.user.username
        )
    user_link.short_description = 'User'

    def item_link(self, obj):
        name = obj.item_name
        if obj.hotel_id:
            url = f'{obj.hotel_id}/change/'
        elif obj.package_id:
            url = f'{obj.package_id}/change/'
        else:
            return 'Deleted'
        return format_html(
            '<a href="{}" target="_blank" style="font-family:monospace;font-size:12px;">{}</a>',
            url, name[:40]
        )
    item_link.short_description = 'Item'

    def content_type_badge(self, obj):
        colors = {'Hotel': '#8B5CF6', 'Package': '#10B981'}
        c = obj.content_type
        color = colors.get(c, '#64748B')
        return format_html(
            '<span style="background:{}15;color:{};padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, color, c
        )
    content_type_badge.short_description = 'Type'

    def verified_badge(self, obj):
        if obj.is_verified_booking:
            return format_html(
                '<i class="bi bi-patch-check-fill" style="color:#2563EB;"></i>'
                '<span style="color:#2563EB;font-size:11px;font-weight:600;margin-left:4px;">Verified</span>'
            )
        return '-'
    verified_badge.short_description = 'Verified'

    def approved_badge(self, obj):
        if obj.is_approved:
            return format_html(
                '<span style="color:#22C55E;font-size:12px;font-weight:600;">Approved</span>'
            )
        return format_html(
            '<span style="color:#EF4444;font-size:12px;font-weight:600;">Hidden</span>'
        )
    approved_badge.short_description = 'Status'

    def helpful_display(self, obj):
        return obj.helpful_count
    helpful_display.short_description = '👍'

    def created_display(self, obj):
        return obj.created_at.strftime('%d %b %Y')
    created_display.short_description = 'Date'

    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} review(s) approved.')

    @admin.action(description='Hide selected reviews')
    def hide_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} review(s) hidden.')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'hotel', 'package')


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'review_link', 'created_at']
    list_per_page = 30

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:60px;height:45px;object-fit:cover;border-radius:4px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Image'

    def review_link(self, obj):
        return format_html(
            '<a href="{}admin/reviews/review/{}/change/" target="_blank">Review #{}</a>',
            obj.review.id, obj.review.id
        )
    review_link.short_description = 'Review'
