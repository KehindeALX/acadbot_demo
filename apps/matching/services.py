"""
Matching service - contains the matching algorithm for student-mentor pairing.
"""
from django.db.models import Count, Q
from django.utils import timezone
from apps.accounts.models import MentorProfile
from apps.careers.models import Career
from .models import Match, MentorMatch


def calculate_compatibility_score(student, mentor_profile, match_request):
    """
    Calculate compatibility score between a student and mentor.

    Factors:
    1. Career alignment (required) - 40 points
    2. Schedule overlap - 25 points
    3. Mentor availability - 15 points
    4. Mentor load balancing - 10 points
    5. Rating/review score - 10 points

    Total: 100 points
    """
    score = 0

    # 1. Career alignment (40 points)
    student_careers = set(match_request.preferred_careers.values_list('id', flat=True))
    mentor_careers = set(mentor_profile.expertise_careers.values_list('id', flat=True))

    if student_careers & mentor_careers:
        # Full match on career
        score += 40
    elif match_request.preferred_careers.exists() and mentor_profile.expertise_careers.exists():
        # Partial match - same general field
        score += 20

    # 2. Schedule overlap (25 points)
    student_schedule = match_request.preferred_schedule or {}
    mentor_availability = mentor_profile.availability_data or {}

    if student_schedule and mentor_availability:
        overlap_score = calculate_schedule_overlap(student_schedule, mentor_availability)
        score += overlap_score * 25
    elif not student_schedule or not mentor_availability:
        # No preference specified, neutral
        score += 12.5

    # 3. Mentor availability (15 points)
    if mentor_profile.is_available and mentor_profile.is_verified:
        score += 15
    elif mentor_profile.is_available:
        score += 10
    else:
        score += 0

    # 4. Mentor load balancing (10 points)
    active_matches = mentor_profile.user.matches_as_mentor.filter(
        status=Match.Status.ACTIVE
    ).count()

    if active_matches == 0:
        score += 10
    elif active_matches <= 2:
        score += 7
    elif active_matches <= 5:
        score += 5
    else:
        score += 2

    # 5. Rating score (10 points)
    if mentor_profile.rating >= 4.5:
        score += 10
    elif mentor_profile.rating >= 4.0:
        score += 8
    elif mentor_profile.rating >= 3.5:
        score += 5
    elif mentor_profile.rating >= 3.0:
        score += 3
    else:
        score += 1

    return round(score, 2)


def calculate_schedule_overlap(student_schedule, mentor_availability):
    """
    Calculate schedule overlap score (0.0 to 1.0).

    Expected format:
    {
        "monday": [{"start": "09:00", "end": "17:00"}],
        "tuesday": [...],
        ...
    }
    """
    if not student_schedule or not mentor_availability:
        return 0.0

    total_overlap = 0
    total_student_slots = 0

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    for day in days:
        student_slots = student_schedule.get(day, [])
        mentor_slots = mentor_availability.get(day, [])

        for s_slot in student_slots:
            total_student_slots += 1
            s_start = time_to_minutes(s_slot.get('start', '00:00'))
            s_end = time_to_minutes(s_slot.get('end', '23:59'))

            for m_slot in mentor_slots:
                m_start = time_to_minutes(m_slot.get('start', '00:00'))
                m_end = time_to_minutes(m_slot.get('end', '23:59'))

                # Calculate overlap
                overlap_start = max(s_start, m_start)
                overlap_end = min(s_end, m_end)

                if overlap_start < overlap_end:
                    overlap_duration = overlap_end - overlap_start
                    slot_duration = s_end - s_start
                    if slot_duration > 0:
                        total_overlap += overlap_duration / slot_duration

    if total_student_slots == 0:
        return 0.5  # Neutral if no student preferences

    return min(total_overlap / total_student_slots, 1.0)


def time_to_minutes(time_str):
    """Convert HH:MM time string to minutes since midnight."""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except (ValueError, AttributeError):
        return 0


def find_best_mentors(match_request, limit=5):
    """
    Find the best mentor matches for a match request.
    Returns a list of (mentor_profile, score) tuples sorted by score.
    """
    # Get verified, available mentors with matching career expertise
    student_careers = match_request.preferred_careers.all()

    if not student_careers.exists():
        # If no specific careers, match with all verified mentors
        mentors = MentorProfile.objects.filter(
            is_verified=True,
            is_available=True,
            user__is_active=True,
        ).select_related('user').prefetch_related('expertise_careers')
    else:
        mentors = MentorProfile.objects.filter(
            is_verified=True,
            is_available=True,
            user__is_active=True,
            expertise_careers__in=student_careers,
        ).select_related('user').prefetch_related('expertise_careers').distinct()

    scored_mentors = []
    for mentor in mentors:
        score = calculate_compatibility_score(
            match_request.student,
            mentor,
            match_request,
        )
        scored_mentors.append((mentor, score))

    # Sort by score descending
    scored_mentors.sort(key=lambda x: x[1], reverse=True)

    return scored_mentors[:limit]


def create_match_suggestions(match_request):
    """
    Create mentor match suggestions for a match request.
    """
    # Clear existing suggestions
    match_request.suggested_mentors.all().delete()

    best_mentors = find_best_mentors(match_request, limit=10)

    suggestions = []
    for mentor, score in best_mentors:
        suggestion = MentorMatch.objects.create(
            match_request=match_request,
            mentor=mentor.user,
            compatibility_score=score,
        )
        suggestions.append(suggestion)

    return suggestions


def auto_match(match_request):
    """
    Automatically create the best match for a match request.
    """
    best_mentors = find_best_mentors(match_request, limit=1)

    if not best_mentors:
        return None

    mentor, score = best_mentors[0]

    match = Match.objects.create(
        match_request=match_request,
        student=match_request.student,
        mentor=mentor.user,
        status=Match.Status.PENDING,
        compatibility_score=score,
    )

    match_request.status = MatchRequest.Status.MATCHED
    match_request.matched_at = timezone.now()
    match_request.save(update_fields=['status', 'matched_at', 'updated_at'])

    return match