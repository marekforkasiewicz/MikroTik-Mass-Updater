"""Compliance Service - Configuration compliance checking and diff"""

import logging
import difflib
import re
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy.orm import Session

from ..models.router import Router
from ..models.compliance import ComplianceBaseline, ComplianceCheck, ComplianceRule
from ..services.routeros_rest import RouterOSClient, RouterOSException
from ..config import settings

logger = logging.getLogger(__name__)


class ComplianceService:
    """Service for configuration compliance checking"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Config Export ====================

    def export_router_config(
        self,
        router_id: int,
        hide_sensitive: bool = True
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Export router configuration.

        Args:
            router_id: Router ID
            hide_sensitive: Hide passwords and sensitive data

        Returns:
            Tuple of (config_content, error_message)
        """
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return None, "Router not found"

        username = router.username or settings.DEFAULT_USERNAME
        password = router.password or settings.DEFAULT_PASSWORD

        if not username or not password:
            return None, "No credentials available"

        try:
            client = RouterOSClient(
                host=router.ip,
                username=username,
                password=password,
                port=443,
                timeout=30
            )

            if not client.connect():
                return None, "Failed to connect to router"

            try:
                config = client.get_export(hide_sensitive=hide_sensitive)
                return config, None
            finally:
                client.close()

        except RouterOSException as e:
            return None, str(e)
        except Exception as e:
            logger.exception(f"Error exporting config from {router.ip}")
            return None, str(e)

    # ==================== Config Diff ====================

    def diff_configs(
        self,
        config_a: str,
        config_b: str,
        label_a: str = "Config A",
        label_b: str = "Config B",
        context_lines: int = 3
    ) -> Dict[str, Any]:
        """
        Compare two configurations and return diff.

        Args:
            config_a: First configuration
            config_b: Second configuration
            label_a: Label for first config
            label_b: Label for second config
            context_lines: Number of context lines

        Returns:
            Dict with unified_diff, added, removed, changed counts
        """
        lines_a = config_a.splitlines(keepends=True)
        lines_b = config_b.splitlines(keepends=True)

        # Generate unified diff
        diff = list(difflib.unified_diff(
            lines_a, lines_b,
            fromfile=label_a,
            tofile=label_b,
            n=context_lines
        ))

        # Count changes
        added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        return {
            "unified_diff": "".join(diff),
            "added_lines": added,
            "removed_lines": removed,
            "has_changes": len(diff) > 0,
            "label_a": label_a,
            "label_b": label_b
        }

    def diff_routers(
        self,
        router_a_id: int,
        router_b_id: int,
        hide_sensitive: bool = True
    ) -> Dict[str, Any]:
        """
        Compare configurations of two routers.

        Returns:
            Dict with diff result or error
        """
        config_a, error_a = self.export_router_config(router_a_id, hide_sensitive)
        if error_a:
            return {"error": f"Router A: {error_a}"}

        config_b, error_b = self.export_router_config(router_b_id, hide_sensitive)
        if error_b:
            return {"error": f"Router B: {error_b}"}

        router_a = self.db.query(Router).filter(Router.id == router_a_id).first()
        router_b = self.db.query(Router).filter(Router.id == router_b_id).first()

        label_a = f"{router_a.identity or router_a.ip} ({router_a.ip})"
        label_b = f"{router_b.identity or router_b.ip} ({router_b.ip})"

        return self.diff_configs(config_a, config_b, label_a, label_b)

    # ==================== Compliance Baseline CRUD ====================

    def create_baseline(
        self,
        name: str,
        description: Optional[str],
        rules: List[Dict[str, Any]],
        tags: List[str] = None
    ) -> ComplianceBaseline:
        """Create a new compliance baseline"""
        baseline = ComplianceBaseline(
            name=name,
            description=description,
            rules=rules,
            tags=tags or [],
            is_active=True
        )
        self.db.add(baseline)
        self.db.commit()
        self.db.refresh(baseline)
        logger.info(f"Baseline created: {baseline.name} (id={baseline.id})")
        return baseline

    def update_baseline(
        self,
        baseline_id: int,
        **kwargs
    ) -> Optional[ComplianceBaseline]:
        """Update a compliance baseline"""
        baseline = self.get_baseline(baseline_id)
        if not baseline:
            return None

        for field, value in kwargs.items():
            if hasattr(baseline, field):
                setattr(baseline, field, value)

        self.db.commit()
        self.db.refresh(baseline)
        logger.info(f"Baseline updated: {baseline.name} (id={baseline.id})")
        return baseline

    def delete_baseline(self, baseline_id: int) -> bool:
        """Delete a compliance baseline"""
        baseline = self.get_baseline(baseline_id)
        if not baseline:
            return False

        self.db.delete(baseline)
        self.db.commit()
        logger.info(f"Baseline deleted: (id={baseline_id})")
        return True

    def get_baseline(self, baseline_id: int) -> Optional[ComplianceBaseline]:
        """Get a baseline by ID"""
        return self.db.query(ComplianceBaseline).filter(
            ComplianceBaseline.id == baseline_id
        ).first()

    def get_baseline_by_name(self, name: str) -> Optional[ComplianceBaseline]:
        """Get a baseline by name"""
        return self.db.query(ComplianceBaseline).filter(
            ComplianceBaseline.name == name
        ).first()

    def list_baselines(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> Tuple[List[ComplianceBaseline], int]:
        """List baselines with optional filters"""
        query = self.db.query(ComplianceBaseline)

        if is_active is not None:
            query = query.filter(ComplianceBaseline.is_active == is_active)

        total = query.count()
        baselines = query.order_by(ComplianceBaseline.name).offset(skip).limit(limit).all()

        return baselines, total

    # ==================== Compliance Checking ====================

    def check_compliance(
        self,
        router_id: int,
        baseline_id: int
    ) -> ComplianceCheck:
        """
        Check router compliance against a baseline.

        Args:
            router_id: Router to check
            baseline_id: Baseline to check against

        Returns:
            ComplianceCheck record with results
        """
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            raise ValueError("Router not found")

        baseline = self.get_baseline(baseline_id)
        if not baseline:
            raise ValueError("Baseline not found")

        # Get router config
        config, error = self.export_router_config(router_id)
        if error:
            # Create failed check record
            check = ComplianceCheck(
                router_id=router_id,
                baseline_id=baseline_id,
                status="error",
                error_message=error,
                results=[]
            )
            self.db.add(check)
            self.db.commit()
            self.db.refresh(check)
            return check

        # Run compliance rules
        results = []
        compliant_count = 0
        non_compliant_count = 0

        for rule in baseline.rules:
            rule_result = self._check_rule(config, rule)
            results.append(rule_result)
            if rule_result["status"] == "compliant":
                compliant_count += 1
            else:
                non_compliant_count += 1

        # Determine overall status
        if non_compliant_count == 0:
            status = "compliant"
        elif compliant_count == 0:
            status = "non_compliant"
        else:
            status = "partial"

        # Create check record
        check = ComplianceCheck(
            router_id=router_id,
            baseline_id=baseline_id,
            status=status,
            compliant_rules=compliant_count,
            non_compliant_rules=non_compliant_count,
            results=results,
            config_snapshot=config
        )
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)

        logger.info(f"Compliance check: router={router_id}, baseline={baseline_id}, status={status}")
        return check

    def _check_rule(self, config: str, rule: Dict) -> Dict[str, Any]:
        """
        Check a single compliance rule against config.

        Rule types:
        - contains: Config must contain the pattern
        - not_contains: Config must NOT contain the pattern
        - regex_match: Config must match regex
        - setting: Specific setting must have specific value
        """
        rule_type = rule.get("type", "contains")
        pattern = rule.get("pattern", "")
        name = rule.get("name", "Unnamed rule")
        severity = rule.get("severity", "warning")
        description = rule.get("description", "")

        result = {
            "name": name,
            "type": rule_type,
            "pattern": pattern,
            "severity": severity,
            "description": description,
            "status": "compliant",
            "details": None
        }

        try:
            if rule_type == "contains":
                if pattern not in config:
                    result["status"] = "non_compliant"
                    result["details"] = f"Required pattern not found: {pattern}"

            elif rule_type == "not_contains":
                if pattern in config:
                    result["status"] = "non_compliant"
                    result["details"] = f"Forbidden pattern found: {pattern}"

            elif rule_type == "regex_match":
                if not re.search(pattern, config, re.MULTILINE):
                    result["status"] = "non_compliant"
                    result["details"] = f"Regex pattern not matched: {pattern}"

            elif rule_type == "regex_not_match":
                if re.search(pattern, config, re.MULTILINE):
                    result["status"] = "non_compliant"
                    result["details"] = f"Forbidden regex pattern matched: {pattern}"

            elif rule_type == "setting":
                # Check for specific setting value
                # Pattern format: "/path/command setting=value"
                setting_path = rule.get("path", "")
                setting_name = rule.get("setting", "")
                expected_value = rule.get("expected", "")

                # Build regex to find the setting
                setting_regex = rf'{re.escape(setting_path)}.*{re.escape(setting_name)}={re.escape(expected_value)}'
                if not re.search(setting_regex, config, re.MULTILINE | re.IGNORECASE):
                    result["status"] = "non_compliant"
                    result["details"] = f"Setting {setting_path} {setting_name} not set to {expected_value}"

        except Exception as e:
            result["status"] = "error"
            result["details"] = f"Rule check error: {e}"

        return result

    def bulk_check_compliance(
        self,
        router_ids: List[int],
        baseline_id: int
    ) -> List[ComplianceCheck]:
        """
        Check compliance for multiple routers.

        Returns:
            List of ComplianceCheck records
        """
        results = []
        for router_id in router_ids:
            try:
                check = self.check_compliance(router_id, baseline_id)
                results.append(check)
            except Exception as e:
                logger.error(f"Compliance check failed for router {router_id}: {e}")
                # Create error record
                check = ComplianceCheck(
                    router_id=router_id,
                    baseline_id=baseline_id,
                    status="error",
                    error_message=str(e),
                    results=[]
                )
                self.db.add(check)
                self.db.commit()
                self.db.refresh(check)
                results.append(check)

        return results

    def get_check(self, check_id: int) -> Optional[ComplianceCheck]:
        """Get a compliance check by ID"""
        return self.db.query(ComplianceCheck).filter(
            ComplianceCheck.id == check_id
        ).first()

    def list_checks(
        self,
        router_id: Optional[int] = None,
        baseline_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ComplianceCheck], int]:
        """List compliance checks with optional filters"""
        query = self.db.query(ComplianceCheck)

        if router_id:
            query = query.filter(ComplianceCheck.router_id == router_id)
        if baseline_id:
            query = query.filter(ComplianceCheck.baseline_id == baseline_id)
        if status:
            query = query.filter(ComplianceCheck.status == status)

        total = query.count()
        checks = query.order_by(ComplianceCheck.checked_at.desc()).offset(skip).limit(limit).all()

        return checks, total

    def get_compliance_summary(self, baseline_id: Optional[int] = None) -> Dict[str, Any]:
        """Get compliance summary across all routers"""
        query = self.db.query(ComplianceCheck)

        if baseline_id:
            query = query.filter(ComplianceCheck.baseline_id == baseline_id)

        # Get latest check for each router
        from sqlalchemy import func
        subquery = self.db.query(
            ComplianceCheck.router_id,
            func.max(ComplianceCheck.checked_at).label('max_checked')
        ).group_by(ComplianceCheck.router_id).subquery()

        latest_checks = query.join(
            subquery,
            (ComplianceCheck.router_id == subquery.c.router_id) &
            (ComplianceCheck.checked_at == subquery.c.max_checked)
        ).all()

        compliant = sum(1 for c in latest_checks if c.status == "compliant")
        partial = sum(1 for c in latest_checks if c.status == "partial")
        non_compliant = sum(1 for c in latest_checks if c.status == "non_compliant")
        error = sum(1 for c in latest_checks if c.status == "error")

        return {
            "total_routers": len(latest_checks),
            "compliant": compliant,
            "partial": partial,
            "non_compliant": non_compliant,
            "error": error,
            "compliance_rate": round(compliant / len(latest_checks) * 100, 1) if latest_checks else 0
        }
