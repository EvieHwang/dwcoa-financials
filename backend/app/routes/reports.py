"""Report generation routes."""

import base64
from typing import Optional

from app.services import pdf_generator


def handle_generate_pdf(year: Optional[int] = None) -> dict:
    """Generate and return PDF report.

    Args:
        year: Report year

    Returns:
        Response with PDF content
    """
    try:
        pdf_bytes = pdf_generator.generate_dashboard_pdf(year)

        # Return as base64 for API Gateway
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/pdf',
                'Content-Disposition': f'attachment; filename="DWCOA_Report_{year or "current"}.pdf"'
            },
            'body': base64.b64encode(pdf_bytes).decode('utf-8'),
            'isBase64Encoded': True
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "internal_error", "message": "{str(e)}"}}'
        }
