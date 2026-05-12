"""Admin plošča za aplikacijo groups."""

from django.contrib import admin

from .models import GroupMembership, GroupMessage, ReadingGroup


@admin.register(ReadingGroup)
class ReadingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'visibility', 'owner', 'member_count', 'created_at')
    list_filter = ('visibility',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('genres',)


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'is_approved', 'joined_at')
    list_filter = ('role', 'is_approved')
    search_fields = ('user__username', 'group__name')
    raw_id_fields = ('user', 'group')


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'group', 'created_at')
    search_fields = ('sender__username', 'group__name', 'content')
    raw_id_fields = ('sender', 'group')
