"""Reports API endpoints"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.report import (
    ReportRequest, ReportResponse, ReportListResponse,
    ReportFilter
)
from ..services.export_service import ExportService
from ..core.deps import CurrentUser, require_permission
from ..core.permissions import Permission

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    current_user: Annotated[None, Depends(require_permission(Permission.EXPORT_REPORTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Generate a report"""
    export_service = ExportService(db)

    try:
        result = export_service.generate_report(request, current_user.id)
        return ReportResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("")
async def list_reports(
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_REPORTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """List generated reports"""
    export_service = ExportService(db)
    reports = export_service.list_reports()

    return {"reports": reports}


@router.get("/download/{filename}")
async def download_report(
    filename: str,
    current_user: Annotated[None, Depends(require_permission(Permission.VIEW_REPORTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Download a generated report"""
    export_service = ExportService(db)
    filepath = export_service.get_report_file(filename)

    if not filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Determine media type
    if filename.endswith('.pdf'):
        media_type = "application/pdf"
    elif filename.endswith('.xlsx'):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif filename.endswith('.csv'):
        media_type = "text/csv"
    else:
        media_type = "application/json"

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type
    )


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    filename: str,
    current_user: Annotated[None, Depends(require_permission(Permission.EXPORT_REPORTS))],
    db: Annotated[Session, Depends(get_db)]
):
    """Delete a generated report"""
    export_service = ExportService(db)
    success = export_service.delete_report(filename)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )


# Quick export endpoints (inline response)
@router.get("/quick/inventory")
async def quick_export_inventory(
    current_user: Annotated[None, Depends(require_permission(Permission.EXPORT_REPORTS))],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query("csv", pattern="^(csv|json)$")
):
    """Quick export of router inventory"""
    export_service = ExportService(db)
    data = export_service._get_inventory_data(ReportFilter())

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["IP", "Identity", "Model", "Version", "Status", "Last Seen"])

        for router in data.get("routers", []):
            writer.writerow([
                router.get("ip"),
                router.get("identity"),
                router.get("model"),
                router.get("ros_version"),
                "Online" if router.get("is_online") else "Offline",
                router.get("last_seen")
            ])

        return {
            "content": output.getvalue(),
            "filename": "inventory.csv",
            "content_type": "text/csv"
        }
    else:
        return data


@router.get("/quick/health")
async def quick_export_health(
    current_user: Annotated[None, Depends(require_permission(Permission.EXPORT_REPORTS))],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query("csv", pattern="^(csv|json)$")
):
    """Quick export of health status"""
    export_service = ExportService(db)
    data = export_service._get_health_data(ReportFilter())

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["IP", "Identity", "Status", "Uptime %", "Latency", "Alerts"])

        for router in data.get("routers", []):
            writer.writerow([
                router.get("router_ip"),
                router.get("router_identity"),
                router.get("status"),
                router.get("uptime_percentage"),
                router.get("avg_latency_ms"),
                router.get("alerts_count")
            ])

        return {
            "content": output.getvalue(),
            "filename": "health.csv",
            "content_type": "text/csv"
        }
    else:
        return data
