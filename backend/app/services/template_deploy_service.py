"""Template Deployment Service - Execute templates on routers via REST API"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from ..models.router import Router
from ..models.task import Task
from ..models.template import ConfigTemplate, TemplateDeployment
from ..services.routeros_rest import RouterOSClient, RouterOSException
from ..services.template_service import TemplateService
from ..services.backup_service import BackupService
from ..core.enums import TaskStatus, TaskType
from ..config import settings

logger = logging.getLogger(__name__)


class TemplateDeployService:
    """Service for deploying templates to routers"""

    def __init__(self, db: Session):
        self.db = db
        self.template_service = TemplateService(db)

    def deploy_to_router(
        self,
        router: Router,
        template: ConfigTemplate,
        variables: Dict[str, Any],
        rendered_content: str,
        deployment: TemplateDeployment,
        write_log: callable = None
    ) -> Dict[str, Any]:
        """
        Deploy a rendered template to a single router.

        Args:
            router: Router to deploy to
            template: The template being deployed
            variables: Variables used for rendering
            rendered_content: Pre-rendered template content
            deployment: Deployment record to update
            write_log: Optional logging callback

        Returns:
            Dict with status, output, error
        """
        result = {
            "router_id": router.id,
            "router_ip": router.ip,
            "router_identity": router.identity,
            "status": "pending",
            "output": None,
            "error": None
        }

        def log(msg: str):
            if write_log:
                write_log(msg)
            logger.info(f"[{router.ip}] {msg}")

        # Get credentials
        username = router.username or settings.DEFAULT_USERNAME
        password = router.password or settings.DEFAULT_PASSWORD

        if not username or not password:
            result["status"] = "failed"
            result["error"] = "No credentials available"
            self._update_deployment(deployment, "failed", result["error"])
            return result

        log(f"Connecting to {router.ip}...")

        try:
            client = RouterOSClient(
                host=router.ip,
                username=username,
                password=password,
                port=443,
                timeout=30
            )

            if not client.connect():
                result["status"] = "failed"
                result["error"] = "Failed to connect to router"
                self._update_deployment(deployment, "failed", result["error"])
                return result

            try:
                log("Connected successfully")

                # Create a unique script name
                script_name = f"ztp_deploy_{uuid.uuid4().hex[:8]}"

                log(f"Creating temporary script: {script_name}")

                # Create script on router
                try:
                    script_result = client.create_script(
                        name=script_name,
                        source=rendered_content,
                        policy=["read", "write", "test", "policy", "reboot"],
                        comment=f"ZTP deployment - {template.name}"
                    )
                    script_id = script_result.get('.id') or script_result.get('ret')
                    log(f"Script created with ID: {script_id}")
                except RouterOSException as e:
                    result["status"] = "failed"
                    result["error"] = f"Failed to create script: {e}"
                    self._update_deployment(deployment, "failed", result["error"])
                    return result

                # Run the script
                log("Executing script...")
                try:
                    success = client.run_script(name=script_name)
                    if success:
                        log("Script executed successfully")
                        result["status"] = "completed"
                        result["output"] = "Script executed successfully"
                    else:
                        result["status"] = "failed"
                        result["error"] = "Script execution returned failure"
                except RouterOSException as e:
                    result["status"] = "failed"
                    result["error"] = f"Script execution failed: {e}"

                # Clean up - delete the temporary script
                log("Cleaning up temporary script...")
                try:
                    # Find script by name to get its ID
                    scripts = client.list_scripts()
                    for s in scripts:
                        if s.get('name') == script_name:
                            client.delete_script(s.get('.id'))
                            log("Temporary script deleted")
                            break
                except Exception as e:
                    log(f"Warning: Failed to delete temporary script: {e}")

                # Update deployment record
                self._update_deployment(
                    deployment,
                    result["status"],
                    result.get("error")
                )

            finally:
                client.close()
                log("Connection closed")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Unexpected error: {str(e)}"
            self._update_deployment(deployment, "failed", result["error"])
            logger.exception(f"Error deploying to {router.ip}")

        return result

    def _update_deployment(
        self,
        deployment: TemplateDeployment,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update deployment record status"""
        deployment.status = status
        if error_message:
            deployment.error_message = error_message
        if status in ('completed', 'failed', 'rolled_back'):
            deployment.completed_at = datetime.utcnow()
        self.db.commit()


def run_template_deploy_task(task_id: str, config: dict, db_url: str):
    """
    Background task for deploying templates to routers.

    Args:
        task_id: Task ID
        config: Task configuration containing:
            - template_id: ID of template to deploy
            - router_ids: List of router IDs
            - variables: Variables for rendering
            - backup_before: Whether to backup before deploy
        db_url: Database URL
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from ..services.task_log_service import TaskLogService

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Setup logging
    log_filename = TaskLogService.get_log_filename(task_id)
    log_filepath = TaskLogService.get_log_filepath(task_id, log_filename)

    def write_log(message: str, update_task_message: bool = False):
        """Write to file and optionally update task for WebSocket"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp} - {message}\n"
        with open(log_filepath, 'a', encoding='utf-8') as f:
            f.write(log_line)
        logger.info(message)

        if update_task_message:
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.current_message = message[:500]
                    db.commit()
            except Exception:
                pass

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.utcnow()
        db.commit()

        write_log("=" * 70)
        write_log(f"TEMPLATE DEPLOYMENT STARTED: {task_id}")
        write_log("=" * 70)

        # Get configuration
        template_id = config.get("template_id")
        router_ids = config.get("router_ids", [])
        variables = config.get("variables", {})
        backup_before = config.get("backup_before", False)

        # Get template
        template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
        if not template:
            task.status = TaskStatus.FAILED.value
            task.error = f"Template not found: {template_id}"
            task.completed_at = datetime.utcnow()
            db.commit()
            write_log(f"ERROR: Template not found: {template_id}")
            return

        write_log(f"Template: {template.name}")
        write_log(f"Category: {template.category}")

        # Get routers
        routers = db.query(Router).filter(Router.id.in_(router_ids)).all()
        if not routers:
            task.status = TaskStatus.FAILED.value
            task.error = "No valid routers found"
            task.completed_at = datetime.utcnow()
            db.commit()
            write_log("ERROR: No valid routers found")
            return

        task.total = len(routers)
        db.commit()

        write_log(f"Target routers: {len(routers)}")
        write_log(f"Backup before: {backup_before}")
        write_log(f"Variables: {list(variables.keys())}")
        write_log("-" * 70)

        # Initialize services
        template_service = TemplateService(db)
        deploy_service = TemplateDeployService(db)

        # Results tracking
        results = {
            "successful": 0,
            "failed": 0,
            "routers": []
        }

        # Process each router
        for i, router in enumerate(routers, 1):
            task.progress = i
            task.current_item = router.ip
            task.current_message = f"Deploying to {router.identity or router.ip}"
            db.commit()

            write_log(f"\n[{i}/{len(routers)}] Processing: {router.identity or router.ip} ({router.ip})")

            # Render template for this router
            try:
                rendered_content = template_service.render_template_for_router(
                    template, router, variables
                )
                write_log(f"  Template rendered successfully ({len(rendered_content)} chars)")
            except Exception as e:
                write_log(f"  ERROR: Failed to render template: {e}")
                results["failed"] += 1
                results["routers"].append({
                    "router_id": router.id,
                    "router_ip": router.ip,
                    "status": "failed",
                    "error": f"Render error: {e}"
                })
                continue

            # Create backup if requested
            backup_id = None
            if backup_before:
                write_log("  Creating backup before deployment...")
                try:
                    backup_service = BackupService(db)
                    backup = backup_service.create_backup(
                        router_id=router.id,
                        backup_type="config",
                        name=f"pre-ztp-{template.name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    )
                    if backup:
                        backup_id = backup.id
                        write_log(f"  Backup created: {backup.id}")
                    else:
                        write_log("  Warning: Backup creation returned None")
                except Exception as e:
                    write_log(f"  Warning: Backup failed: {e}")

            # Create deployment record
            deployment = TemplateDeployment(
                template_id=template.id,
                router_id=router.id,
                rendered_content=rendered_content,
                variables_used=variables,
                status="running",
                backup_id=backup_id
            )
            db.add(deployment)
            db.commit()
            db.refresh(deployment)

            # Deploy to router
            result = deploy_service.deploy_to_router(
                router=router,
                template=template,
                variables=variables,
                rendered_content=rendered_content,
                deployment=deployment,
                write_log=lambda msg: write_log(f"  {msg}")
            )

            if result["status"] == "completed":
                results["successful"] += 1
                write_log(f"  Result: SUCCESS")
            else:
                results["failed"] += 1
                write_log(f"  Result: FAILED - {result.get('error', 'Unknown error')}")

            results["routers"].append(result)

        # Task completed
        write_log("-" * 70)
        write_log(f"DEPLOYMENT COMPLETED")
        write_log(f"  Successful: {results['successful']}/{len(routers)}")
        write_log(f"  Failed: {results['failed']}/{len(routers)}")
        write_log("=" * 70)

        task.status = TaskStatus.COMPLETED.value if results["failed"] == 0 else TaskStatus.COMPLETED.value
        task.results = results
        task.completed_at = datetime.utcnow()
        task.current_item = None
        task.current_message = f"Completed: {results['successful']} successful, {results['failed']} failed"
        db.commit()

    except Exception as e:
        logger.exception(f"Template deployment task failed: {e}")
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED.value
                task.error = str(e)
                task.completed_at = datetime.utcnow()
                db.commit()
            write_log(f"TASK FAILED: {e}")
        except Exception:
            pass
    finally:
        db.close()
