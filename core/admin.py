# core/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'status', 'has_reply_display', 'show_on_homepage', 'created_at']
    list_filter = ['status', 'show_on_homepage', 'created_at']
    search_fields = ['name', 'email', 'message', 'admin_reply']
    list_editable = ['status', 'show_on_homepage']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'name', 'email')
        }),
        ('User Feedback', {
            'fields': ('message',)
        }),
        ('Admin Response', {
            'fields': ('admin_reply', 'replied_at'),
            'description': 'Write your reply here. It will be displayed on homepage below user feedback.'
        }),
        ('Display Settings', {
            'fields': ('status', 'show_on_homepage'),
            'description': 'Set status to "approved" and check "show on homepage" to display on website.'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'replied_at']
    
    actions = ['approve_feedback', 'reject_feedback']
    
    def has_reply_display(self, obj):
        if obj.has_reply:
            return "✅ Yes"
        return "❌ No"
    has_reply_display.short_description = 'Has Reply'
    
    def save_model(self, request, obj, form, change):
        # If admin_reply is added and replied_at is empty, set it
        if obj.admin_reply and obj.admin_reply.strip() and not obj.replied_at:
            obj.replied_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    def approve_feedback(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f'{queryset.count()} feedback(s) approved.')
    approve_feedback.short_description = "Approve selected feedback"
    
    def reject_feedback(self, request, queryset):
        queryset.update(status='rejected', show_on_homepage=False)
        self.message_user(request, f'{queryset.count()} feedback(s) rejected.')
    reject_feedback.short_description = "Reject selected feedback"