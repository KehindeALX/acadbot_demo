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
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Check if user is the owner
            if hasattr(obj, 'student') and obj.student.user == request.user:
                return True
            if hasattr(obj, 'user') and obj.user == request.user:
                return True
            # Check if user is the mentor
            if hasattr(obj, 'mentor') and obj.mentor.user == request.user:
                return True
            if hasattr(obj, 'match') and obj.match.mentor.user == request.user:
                return True
            # Check if admin
            if request.user.role == 'ADMIN':
                return True
            return False
        return False