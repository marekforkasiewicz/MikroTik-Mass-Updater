"""Custom script service"""

import logging
import re
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy.orm import Session

from ..models.script import CustomScript, ScriptExecution
from ..models.router import Router
from ..schemas.script import ScriptCreate, ScriptUpdate, ScriptVariable
from .router_service import RouterService, HostInfo

logger = logging.getLogger(__name__)


class ScriptService:
    """Service for managing and executing custom scripts"""

    def __init__(self, db: Session):
        self.db = db

    def create_script(self, script_data: ScriptCreate, user_id: Optional[int] = None) -> CustomScript:
        """Create a new custom script"""
        script = CustomScript(
            name=script_data.name,
            description=script_data.description,
            script_type=script_data.script_type,
            content=script_data.content,
            variables=[v.model_dump() for v in script_data.variables],
            timeout=script_data.timeout,
            requires_reboot=script_data.requires_reboot,
            dangerous=script_data.dangerous,
            category=script_data.category,
            tags=script_data.tags,
            allowed_roles=script_data.allowed_roles,
            enabled=script_data.enabled,
            created_by=user_id
        )

        self.db.add(script)
        self.db.commit()
        self.db.refresh(script)
        logger.info(f"Script created: {script.name}")
        return script

    def update_script(
        self,
        script_id: int,
        script_data: ScriptUpdate,
        user_id: Optional[int] = None
    ) -> Optional[CustomScript]:
        """Update a custom script"""
        script = self.db.query(CustomScript).filter(CustomScript.id == script_id).first()
        if not script:
            return None

        update_data = script_data.model_dump(exclude_unset=True)

        if "variables" in update_data and update_data["variables"]:
            update_data["variables"] = [
                v.model_dump() if hasattr(v, 'model_dump') else v
                for v in update_data["variables"]
            ]

        for field, value in update_data.items():
            setattr(script, field, value)

        script.updated_by = user_id
        script.validated = False  # Mark as needing re-validation

        self.db.commit()
        self.db.refresh(script)
        logger.info(f"Script updated: {script.name}")
        return script

    def delete_script(self, script_id: int) -> bool:
        """Delete a script"""
        script = self.db.query(CustomScript).filter(CustomScript.id == script_id).first()
        if not script:
            return False

        self.db.delete(script)
        self.db.commit()
        logger.info(f"Script deleted: {script.name}")
        return True

    def get_script(self, script_id: int) -> Optional[CustomScript]:
        """Get script by ID"""
        return self.db.query(CustomScript).filter(CustomScript.id == script_id).first()

    def get_script_by_name(self, name: str) -> Optional[CustomScript]:
        """Get script by name"""
        return self.db.query(CustomScript).filter(CustomScript.name == name).first()

    def list_scripts(
        self,
        category: Optional[str] = None,
        enabled_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CustomScript], int]:
        """List scripts"""
        query = self.db.query(CustomScript)

        if category:
            query = query.filter(CustomScript.category == category)
        if enabled_only:
            query = query.filter(CustomScript.enabled == True)

        total = query.count()
        scripts = query.offset(skip).limit(limit).all()
        return scripts, total

    def validate_script(self, content: str, script_type: str = "routeros") -> Dict[str, Any]:
        """Validate script syntax"""
        errors = []
        warnings = []

        if script_type == "routeros":
            errors, warnings = self._validate_routeros_script(content)
        elif script_type == "ssh":
            errors, warnings = self._validate_ssh_script(content)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _validate_routeros_script(self, content: str) -> Tuple[List[str], List[str]]:
        """Validate RouterOS script syntax"""
        errors = []
        warnings = []

        lines = content.split('\n')
        brace_count = 0
        paren_count = 0

        dangerous_commands = [
            "/system reset-configuration",
            "/file remove",
            "/system package uninstall",
            "/system routerboard reset"
        ]

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments and empty lines
            if stripped.startswith('#') or not stripped:
                continue

            # Check braces balance
            brace_count += stripped.count('{') - stripped.count('}')
            paren_count += stripped.count('(') - stripped.count(')')

            # Check for dangerous commands
            for cmd in dangerous_commands:
                if cmd in stripped.lower():
                    warnings.append(f"Line {i}: Potentially dangerous command: {cmd}")

            # Check for unclosed strings
            quote_count = stripped.count('"') - stripped.count('\\"')
            if quote_count % 2 != 0:
                errors.append(f"Line {i}: Unclosed string literal")

        if brace_count != 0:
            errors.append(f"Unbalanced braces: {'+' if brace_count > 0 else ''}{brace_count}")

        if paren_count != 0:
            errors.append(f"Unbalanced parentheses: {'+' if paren_count > 0 else ''}{paren_count}")

        return errors, warnings

    def _validate_ssh_script(self, content: str) -> Tuple[List[str], List[str]]:
        """Validate SSH/bash script syntax"""
        errors = []
        warnings = []

        dangerous_patterns = [
            (r'rm\s+-rf\s+/', "Dangerous rm -rf command"),
            (r'mkfs', "Filesystem formatting command"),
            (r'dd\s+if=', "Low-level disk write command"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, content):
                warnings.append(message)

        return errors, warnings

    def execute_script(
        self,
        script_id: int,
        router_id: int,
        variables: Dict[str, Any] = None,
        user_id: Optional[int] = None,
        dry_run: bool = False
    ) -> ScriptExecution:
        """Execute a script on a router"""
        script = self.get_script(script_id)
        if not script:
            raise ValueError("Script not found")

        if not script.enabled:
            raise ValueError("Script is disabled")

        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            raise ValueError("Router not found")

        # Validate required variables
        variables = variables or {}
        for var in script.variables:
            var_data = var if isinstance(var, dict) else var.model_dump()
            if var_data.get("required") and var_data["name"] not in variables:
                if var_data.get("default") is not None:
                    variables[var_data["name"]] = var_data["default"]
                else:
                    raise ValueError(f"Required variable missing: {var_data['name']}")

        # Create execution record
        execution = ScriptExecution(
            script_id=script.id,
            router_id=router.id,
            variables_used=variables,
            status="running",
            executed_by=user_id
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        if dry_run:
            execution.status = "success"
            execution.output = "[DRY RUN] Script would be executed with variables: " + str(variables)
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = 0
            self.db.commit()
            return execution

        try:
            start_time = datetime.utcnow()

            # Substitute variables in script content
            script_content = self._substitute_variables(script.content, variables)

            if script.script_type == "routeros":
                output, return_value = self._execute_routeros_script(router, script_content, script.timeout)
            else:
                output, return_value = self._execute_ssh_script(router, script_content, script.timeout)

            execution.status = "success"
            execution.output = output
            execution.return_value = return_value
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int((execution.completed_at - start_time).total_seconds() * 1000)

            # Update script stats
            script.execution_count += 1
            script.last_executed = datetime.utcnow()

        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            logger.error(f"Script execution failed: {e}")

        self.db.commit()
        self.db.refresh(execution)
        return execution

    def _substitute_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in script content"""
        result = content
        for name, value in variables.items():
            # Replace $variable and ${variable} patterns
            result = result.replace(f"${{{name}}}", str(value))
            result = result.replace(f"${name}", str(value))
        return result

    def _execute_routeros_script(
        self,
        router: Router,
        script_content: str,
        timeout: int
    ) -> Tuple[str, Any]:
        """Execute RouterOS script on router"""
        from ..config import settings

        host = HostInfo(
            ip=router.ip,
            port=router.port,
            username=router.username,
            password=router.password
        )

        api = RouterService.connect(
            host,
            default_username=settings.DEFAULT_USERNAME or "",
            default_password=settings.DEFAULT_PASSWORD or "",
            timeout=timeout
        )

        if not api:
            raise Exception("Failed to connect to router")

        try:
            output_lines = []

            # Parse script and execute commands directly where possible
            lines = script_content.strip().split('\n')

            for line in lines:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Skip :put, :log and variable assignments - they don't produce API output
                if line.startswith(':put') or line.startswith(':log') or line.startswith(':local') or line.startswith(':global'):
                    continue

                # Try to execute as API path command
                try:
                    # Handle /path/to/resource print style commands
                    if line.startswith('/'):
                        from .routeros_rest import RouterOSClient

                        # Parse path like "/ip service print" or "/certificate print"
                        parts = line.split()

                        # Find where the path ends and action begins
                        # Actions are: print, add, set, remove, enable, disable, etc.
                        actions = ['print', 'add', 'set', 'remove', 'enable', 'disable', 'export', 'get']
                        path_str = ''
                        action = 'print'
                        action_idx = len(parts)

                        for i, part in enumerate(parts):
                            if part.lower() in actions:
                                action = part.lower()
                                action_idx = i
                                break

                        # Build path from parts before action
                        path_tokens = []
                        for i in range(action_idx):
                            # Split each part by / and add to tokens
                            for token in parts[i].strip('/').split('/'):
                                if token:
                                    path_tokens.append(token)

                        if path_tokens:
                            # Build the API path
                            path_string = '/' + '/'.join(path_tokens)

                            if isinstance(api, RouterOSClient):
                                # Use REST API client
                                path = api.path(path_string)
                            else:
                                # Legacy librouteros API
                                path = api.path('/' + path_tokens[0], *path_tokens[1:])

                            if action == 'print':
                                results = list(path)
                                if results:
                                    output_lines.append(f"=== /{'/'.join(path_tokens)} ===")
                                    for item in results:
                                        item_str = ', '.join(f"{k}={v}" for k, v in item.items() if not k.startswith('.'))
                                        output_lines.append(f"  {item_str}")
                                else:
                                    output_lines.append(f"=== /{'/'.join(path_tokens)} === (empty)")
                            else:
                                result = tuple(path(action))
                                output_lines.append(f"/{'/'.join(path_tokens)} {action}: {result}")

                except Exception as cmd_error:
                    output_lines.append(f"[{line[:50]}]: {str(cmd_error)}")

            # If no direct commands worked, fall back to script execution
            if not output_lines:
                from .routeros_rest import RouterOSClient
                script_name = f"_temp_script_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

                if isinstance(api, RouterOSClient):
                    # Use REST API client directly
                    script = api.create_script(
                        name=script_name,
                        source=script_content,
                        policy=["read", "write", "test", "reboot"]
                    )
                    script_id = script.get('.id')
                    result = api.run_script(script_id=script_id)

                    # Cleanup
                    try:
                        api.delete_script(script_id)
                    except Exception:
                        pass
                else:
                    # Legacy librouteros API
                    script_path = api.path('/system', 'script')
                    tuple(script_path('add', name=script_name, source=script_content))
                    result = tuple(script_path('run', number=script_name))

                    # Cleanup
                    try:
                        from librouteros.query import Key
                        name_key = Key('name')
                        scripts = list(script_path.select(name_key).where(name_key == script_name))
                        if scripts:
                            tuple(script_path('remove', numbers=scripts[0]['.id']))
                    except Exception:
                        pass

                output_lines.append("Script executed (no direct output available)")
                output_lines.append(f"Result: {result}")

            return '\n'.join(output_lines), None

        finally:
            api.close()

    def _execute_ssh_script(
        self,
        router: Router,
        script_content: str,
        timeout: int
    ) -> Tuple[str, Any]:
        """Execute script via SSH"""
        from .ssh_service import SSHService

        ssh = SSHService()
        success, output, error = ssh.execute_command(
            ip=router.ip,
            username=router.username,
            password=router.password,
            command=script_content,
            timeout=timeout
        )

        if not success and error:
            return f"{output}\nError: {error}" if output else error, 1
        return output, 0

    def get_executions(
        self,
        script_id: Optional[int] = None,
        router_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ScriptExecution], int]:
        """Get script execution history"""
        query = self.db.query(ScriptExecution)

        if script_id:
            query = query.filter(ScriptExecution.script_id == script_id)
        if router_id:
            query = query.filter(ScriptExecution.router_id == router_id)
        if status:
            query = query.filter(ScriptExecution.status == status)

        total = query.count()
        executions = query.order_by(ScriptExecution.started_at.desc()).offset(skip).limit(limit).all()
        return executions, total

    def get_categories(self) -> List[str]:
        """Get list of unique script categories"""
        result = self.db.query(CustomScript.category).distinct().all()
        return [r[0] for r in result if r[0]]
