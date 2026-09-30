"""
Certificate issuing, listing, PDF generation and public verification.
"""
import io

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas as pdfcanvas

from .models import Certificate, Enrollment
from .serializers import CertificateSerializer, CertificateVerifySerializer

NAVY = HexColor('#050B2E')
GOLD = HexColor('#D4AF37')


def build_certificate_pdf(certificate):
    """Render a certificate to PDF bytes. Nothing is written to disk."""
    buffer = io.BytesIO()
    width, height = landscape(A4)

    pdf = pdfcanvas.Canvas(buffer, pagesize=landscape(A4))
    pdf.setTitle(f'Certificate - {certificate.course.title}')

    pdf.setFillColor(NAVY)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(3)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)
    pdf.setLineWidth(1)
    pdf.rect(34, 34, width - 68, height - 68, fill=0, stroke=1)

    centre = width / 2

    pdf.setFillColor(GOLD)
    pdf.setFont('Times-Bold', 30)
    pdf.drawCentredString(centre, height - 130, 'Certificate of Completion')

    pdf.setFont('Times-Roman', 13)
    pdf.drawCentredString(centre, height - 168, 'MORE SUCCESS ACADEMY')

    pdf.setStrokeColor(GOLD)
    pdf.setLineWidth(1)
    pdf.line(centre - 90, height - 182, centre + 90, height - 182)

    pdf.setFillColor(HexColor('#F2F2F2'))
    pdf.setFont('Times-Italic', 14)
    pdf.drawCentredString(centre, height - 240, 'This certifies that')

    pdf.setFillColor(NAVY)
    pdf.setFont('Helvetica-Bold', 30)
    pdf.drawCentredString(centre, height - 290, certificate.holder_name.upper())

    pdf.setFillColor(HexColor('#F2F2F2'))
    pdf.setFont('Times-Italic', 14)
    pdf.drawCentredString(centre, height - 330, 'has successfully completed')

    pdf.setFillColor(NAVY)
    pdf.setFont('Times-Bold', 22)
    pdf.drawCentredString(centre, height - 375, certificate.course.title)

    pdf.setFillColor(HexColor('#F2F2F2'))
    pdf.setFont('Times-Roman', 13)
    issued = certificate.issued_at.strftime('%d %B %Y')
    pdf.drawCentredString(centre, 165, f'Issued on {issued}')

    pdf.drawCentredString(centre, 140, f'Certificate ID: {certificate.code}')

    verify_url = f'{settings.CERT_VERIFY_BASE_URL}?code={certificate.code}'
    pdf.setFont('Times-Roman', 10)
    pdf.drawCentredString(centre, 100, f'Verify at {verify_url}')

    pdf.setFillColor(GOLD)
    pdf.setFont('Times-Bold', 12)
    pdf.drawCentredString(centre, 70, 'More Success Academy')

    pdf.showPage()
    pdf.save()

    return buffer.getvalue()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def issue_certificate(request, course_id):
    """Issue a certificate for a completed, reviewed course."""
    enrollment = get_object_or_404(
        Enrollment.objects.select_related('course', 'course__career'),
        student=request.user,
        course_id=course_id,
    )

    existing = Certificate.objects.filter(user=request.user, course=enrollment.course).first()
    if existing:
        serializer = CertificateSerializer(existing, context={'request': request})
        return Response(
            {
                'success': True,
                'message': 'Certificate already issued.',
                'data': serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    blockers = enrollment.certificate_blockers()
    if blockers:
        return Response(
            {
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'You are not yet eligible for a certificate.',
                    'blockers': blockers,
                },
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    certificate = Certificate.objects.create(
        user=request.user,
        course=enrollment.course,
        score=enrollment.quiz_average(),
    )

    serializer = CertificateSerializer(certificate, context={'request': request})
    return Response(
        {
            'success': True,
            'message': 'Certificate issued.',
            'data': serializer.data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_certificates(request):
    """List the current student's certificates."""
    certificates = Certificate.objects.filter(
        user=request.user
    ).select_related('course', 'course__career')

    serializer = CertificateSerializer(certificates, many=True, context={'request': request})
    return Response({'success': True, 'data': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def certificate_pdf(request, code):
    """Return the certificate PDF. Only the owner may download it."""
    certificate = get_object_or_404(
        Certificate.objects.select_related('user', 'course', 'course__career'),
        code=code,
    )

    if certificate.user_id != request.user.id:
        return Response(
            {
                'success': False,
                'error': {'code': 403, 'message': 'This certificate belongs to another student.'},
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    pdf_bytes = build_certificate_pdf(certificate)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="certificate-{certificate.code}.pdf"'
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_certificate(request, code):
    """Public verification. Returns only name, course, date and validity."""
    certificate = get_object_or_404(
        Certificate.objects.select_related('user', 'course'),
        code=code,
    )

    serializer = CertificateVerifySerializer(certificate)
    return Response({'success': True, 'data': serializer.data})
