"""
Custom permissions for the AcadBot API.
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` or `user` field.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.user == request.user or getattr(obj, 'owner', None) == request.user


class IsStudent(permissions.BasePermission):
    """
    Permission to check if user is a student.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'STUDENT'


class IsMentor(permissions.BasePermission):
    """
    Permission to check if user is a mentor.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'MENTOR'


class IsAdmin(permissions.BasePermission):
    """
    Permission to check if user is an admin.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


# Alias for backward compatibility
IsAdminUser = IsAdmin


class IsStudentOrMentor(permissions.BasePermission):
    """
    Permission to check if user is a student or mentor.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['STUDENT', 'MENTOR']


class IsMentorOrAdmin(permissions.BasePermission):
    """
    Permission to check if user is a mentor or admin.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['MENTOR', 'ADMIN']


class IsOwnerOrMentorOrAdmin(permissions.BasePermission):
    """
    Permission for objects that can be accessed by owner, their mentor, or admin.

    Note: student and mentor fields are ForeignKeys directly to User (AUTH_USER_MODEL),
    not to StudentProfile/MentorProfile, so compare directly to request.user.
    """

    def has_object_permission(self, request, view, obj):
        # Check if user is the owner (student)
        is_owner = getattr(obj, 'student', None) == request.user or getattr(obj, 'user', None) == request.user

        # Check if user is the mentor
        is_mentor = getattr(obj, 'mentor', None) == request.user or (
            hasattr(obj, 'match') and obj.match.mentor == request.user
        )

        # Check if admin
        is_admin = request.user.role == 'ADMIN'

        # Check SessionRecurrence: access via the underlying session
        if not (is_owner or is_mentor) and hasattr(obj, 'session'):
            is_owner = obj.session.student == request.user
            is_mentor = obj.session.mentor == request.user

        # Read permissions: owner, mentor, or admin can view
        if request.method in permissions.SAFE_METHODS:
            return is_owner or is_mentor or is_admin

        # Write permissions (PATCH/PUT/DELETE): owner, mentor, or admin can modify
        return is_owner or is_mentor or is_admin