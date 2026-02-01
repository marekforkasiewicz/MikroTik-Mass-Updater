"""Template service for managing configuration templates and Jinja2 rendering"""

import logging
import fnmatch
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError, StrictUndefined
from sqlalchemy.orm import Session

from ..models.template import ConfigTemplate, DeviceProfile, TemplateDeployment, profile_templates
from ..models.router import Router
from ..schemas.template import (
    TemplateCreate, TemplateUpdate, TemplatePreviewRequest,
    ProfileCreate, ProfileUpdate
)

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing configuration templates"""

    def __init__(self, db: Session):
        self.db = db
        # Jinja2 environment with custom settings
        self.jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=False,  # RouterOS commands shouldn't be escaped
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined  # Raise error on undefined variables
        )
        # Add custom filters and globals
        self._setup_jinja_env()

    def _setup_jinja_env(self):
        """Setup custom Jinja2 filters and globals"""
        # Custom filters
        self.jinja_env.filters['lower'] = str.lower
        self.jinja_env.filters['upper'] = str.upper
        self.jinja_env.filters['yesno'] = lambda v: 'yes' if v else 'no'
        self.jinja_env.filters['quote'] = lambda v: f'"{v}"' if v else '""'

        # Custom globals
        self.jinja_env.globals['now'] = lambda: datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    # ==================== Template CRUD ====================

    def create_template(self, data: TemplateCreate) -> ConfigTemplate:
        """Create a new configuration template"""
        # Validate template syntax first
        errors = self._validate_jinja_syntax(data.content)
        if errors:
            raise ValueError(f"Invalid template syntax: {'; '.join(errors)}")

        template = ConfigTemplate(
            name=data.name,
            description=data.description,
            category=data.category,
            content=data.content,
            variables=[v.model_dump() for v in data.variables],
            tags=data.tags,
            is_active=data.is_active
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Template created: {template.name} (id={template.id})")
        return template

    def update_template(self, template_id: int, data: TemplateUpdate) -> Optional[ConfigTemplate]:
        """Update a configuration template"""
        template = self.get_template(template_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Validate new content if provided
        if 'content' in update_data:
            errors = self._validate_jinja_syntax(update_data['content'])
            if errors:
                raise ValueError(f"Invalid template syntax: {'; '.join(errors)}")

        # Convert variables if provided
        if 'variables' in update_data and update_data['variables'] is not None:
            update_data['variables'] = [v.model_dump() if hasattr(v, 'model_dump') else v for v in update_data['variables']]

        for field, value in update_data.items():
            setattr(template, field, value)

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Template updated: {template.name} (id={template.id})")
        return template

    def delete_template(self, template_id: int) -> bool:
        """Delete a configuration template"""
        template = self.get_template(template_id)
        if not template:
            return False

        self.db.delete(template)
        self.db.commit()
        logger.info(f"Template deleted: {template.name} (id={template_id})")
        return True

    def get_template(self, template_id: int) -> Optional[ConfigTemplate]:
        """Get a template by ID"""
        return self.db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()

    def get_template_by_name(self, name: str) -> Optional[ConfigTemplate]:
        """Get a template by name"""
        return self.db.query(ConfigTemplate).filter(ConfigTemplate.name == name).first()

    def list_templates(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[List[ConfigTemplate], int]:
        """List templates with optional filters"""
        query = self.db.query(ConfigTemplate)

        if category:
            query = query.filter(ConfigTemplate.category == category)
        if is_active is not None:
            query = query.filter(ConfigTemplate.is_active == is_active)

        total = query.count()
        templates = query.order_by(ConfigTemplate.name).offset(skip).limit(limit).all()

        # Filter by tags in Python (JSON column filtering varies by database)
        if tags:
            templates = [t for t in templates if any(tag in (t.tags or []) for tag in tags)]
            total = len(templates)

        return templates, total

    def get_categories(self) -> List[str]:
        """Get list of distinct categories"""
        result = self.db.query(ConfigTemplate.category).distinct().all()
        return sorted([r[0] for r in result if r[0]])

    # ==================== Template Rendering ====================

    def validate_template(self, content: str) -> Tuple[bool, List[str], List[str]]:
        """Validate template syntax"""
        errors = self._validate_jinja_syntax(content)
        warnings = []

        # Check for common issues
        if '{{' in content and '}}' not in content:
            warnings.append("Unclosed variable block detected")
        if '{%' in content and '%}' not in content:
            warnings.append("Unclosed control block detected")

        return len(errors) == 0, errors, warnings

    def _validate_jinja_syntax(self, content: str) -> List[str]:
        """Validate Jinja2 syntax and return list of errors"""
        errors = []
        try:
            self.jinja_env.parse(content)
        except TemplateSyntaxError as e:
            errors.append(f"Line {e.lineno}: {e.message}")
        except Exception as e:
            errors.append(str(e))
        return errors

    def preview_template(
        self,
        template_id: int,
        router_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Preview rendered template with variables"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        context = self._build_render_context(template, router_id, variables)
        rendered = self._render_template(template.content, context)

        return rendered, context

    def render_template_for_router(
        self,
        template: ConfigTemplate,
        router: Router,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render a template for a specific router"""
        context = self._build_render_context(template, router.id, variables)
        return self._render_template(template.content, context)

    def _build_render_context(
        self,
        template: ConfigTemplate,
        router_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build context for template rendering"""
        context = {}

        # Add default values from template variables
        for var in (template.variables or []):
            if var.get('default') is not None:
                context[var['name']] = var['default']

        # Add router context if provided
        if router_id:
            router = self.db.query(Router).filter(Router.id == router_id).first()
            if router:
                context['router'] = {
                    'id': router.id,
                    'ip': router.ip,
                    'identity': router.identity or 'MikroTik',
                    'model': router.model or 'Unknown',
                    'ros_version': router.ros_version,
                    'firmware': router.firmware,
                    'architecture': router.architecture,
                    'uptime': router.uptime,
                    'memory_total_mb': router.memory_total_mb,
                    'location': router.location,
                    'tags': router.tags or []
                }
        else:
            # Provide sample router for preview
            context['router'] = {
                'id': 0,
                'ip': '192.168.1.1',
                'identity': 'Sample-Router',
                'model': 'hAP ac²',
                'ros_version': '7.14',
                'firmware': '7.14',
                'architecture': 'arm',
                'uptime': '1w2d3h4m',
                'memory_total_mb': 128,
                'location': 'Sample Location',
                'tags': ['sample', 'test']
            }

        # Override with provided variables
        if variables:
            context.update(variables)

        return context

    def _render_template(self, content: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with context"""
        try:
            template = self.jinja_env.from_string(content)
            return template.render(**context)
        except UndefinedError as e:
            raise ValueError(f"Undefined variable: {e}")
        except Exception as e:
            raise ValueError(f"Render error: {e}")

    # ==================== Device Profile CRUD ====================

    def create_profile(self, data: ProfileCreate) -> DeviceProfile:
        """Create a new device profile"""
        profile = DeviceProfile(
            name=data.name,
            description=data.description,
            device_filter=data.device_filter.model_dump(),
            execution_order=data.execution_order,
            variables=data.variables,
            is_active=data.is_active
        )

        # Associate templates
        if data.template_ids:
            templates = self.db.query(ConfigTemplate).filter(
                ConfigTemplate.id.in_(data.template_ids)
            ).all()
            profile.templates = templates

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"Profile created: {profile.name} (id={profile.id})")
        return profile

    def update_profile(self, profile_id: int, data: ProfileUpdate) -> Optional[DeviceProfile]:
        """Update a device profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle template_ids separately
        template_ids = update_data.pop('template_ids', None)
        if template_ids is not None:
            templates = self.db.query(ConfigTemplate).filter(
                ConfigTemplate.id.in_(template_ids)
            ).all()
            profile.templates = templates

        # Convert device_filter if provided
        if 'device_filter' in update_data and update_data['device_filter'] is not None:
            update_data['device_filter'] = update_data['device_filter'].model_dump() if hasattr(update_data['device_filter'], 'model_dump') else update_data['device_filter']

        for field, value in update_data.items():
            setattr(profile, field, value)

        self.db.commit()
        self.db.refresh(profile)
        logger.info(f"Profile updated: {profile.name} (id={profile.id})")
        return profile

    def delete_profile(self, profile_id: int) -> bool:
        """Delete a device profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return False

        self.db.delete(profile)
        self.db.commit()
        logger.info(f"Profile deleted: {profile.name} (id={profile_id})")
        return True

    def get_profile(self, profile_id: int) -> Optional[DeviceProfile]:
        """Get a profile by ID"""
        return self.db.query(DeviceProfile).filter(DeviceProfile.id == profile_id).first()

    def get_profile_by_name(self, name: str) -> Optional[DeviceProfile]:
        """Get a profile by name"""
        return self.db.query(DeviceProfile).filter(DeviceProfile.name == name).first()

    def list_profiles(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> Tuple[List[DeviceProfile], int]:
        """List profiles with optional filters"""
        query = self.db.query(DeviceProfile)

        if is_active is not None:
            query = query.filter(DeviceProfile.is_active == is_active)

        total = query.count()
        profiles = query.order_by(DeviceProfile.name).offset(skip).limit(limit).all()

        return profiles, total

    # ==================== Device Profile Matching ====================

    def match_router_to_profiles(self, router: Router) -> List[DeviceProfile]:
        """Find profiles that match a router based on device_filter"""
        profiles, _ = self.list_profiles(is_active=True)
        matched = []

        for profile in profiles:
            if self._router_matches_filter(router, profile.device_filter):
                matched.append(profile)

        return matched

    def _router_matches_filter(self, router: Router, device_filter: Dict) -> bool:
        """Check if a router matches a device filter"""
        if not device_filter:
            return True  # Empty filter matches all

        # Check model patterns
        model_patterns = device_filter.get('model', [])
        if model_patterns and router.model:
            model_match = any(
                fnmatch.fnmatch(router.model, pattern)
                for pattern in model_patterns
            )
            if not model_match:
                return False

        # Check architecture
        architectures = device_filter.get('architecture', [])
        if architectures and router.architecture:
            if router.architecture not in architectures:
                return False

        return True

    def get_routers_for_profile(self, profile_id: int) -> List[Router]:
        """Get all routers that match a profile's device_filter"""
        profile = self.get_profile(profile_id)
        if not profile:
            return []

        routers = self.db.query(Router).all()
        return [r for r in routers if self._router_matches_filter(r, profile.device_filter)]

    # ==================== Template Deployment ====================

    def create_deployment(
        self,
        template_id: int,
        router_id: int,
        rendered_content: str,
        variables_used: Dict[str, Any],
        backup_id: Optional[int] = None
    ) -> TemplateDeployment:
        """Create a deployment record"""
        deployment = TemplateDeployment(
            template_id=template_id,
            router_id=router_id,
            rendered_content=rendered_content,
            variables_used=variables_used,
            backup_id=backup_id,
            status="pending"
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def update_deployment_status(
        self,
        deployment_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[TemplateDeployment]:
        """Update deployment status"""
        deployment = self.db.query(TemplateDeployment).filter(
            TemplateDeployment.id == deployment_id
        ).first()

        if not deployment:
            return None

        deployment.status = status
        if error_message:
            deployment.error_message = error_message
        if status in ('completed', 'failed', 'rolled_back'):
            deployment.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def list_deployments(
        self,
        template_id: Optional[int] = None,
        router_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[TemplateDeployment], int]:
        """List deployment records with optional filters"""
        query = self.db.query(TemplateDeployment)

        if template_id:
            query = query.filter(TemplateDeployment.template_id == template_id)
        if router_id:
            query = query.filter(TemplateDeployment.router_id == router_id)
        if status:
            query = query.filter(TemplateDeployment.status == status)

        total = query.count()
        deployments = query.order_by(TemplateDeployment.deployed_at.desc()).offset(skip).limit(limit).all()

        return deployments, total

    def get_deployment(self, deployment_id: int) -> Optional[TemplateDeployment]:
        """Get a deployment by ID"""
        return self.db.query(TemplateDeployment).filter(
            TemplateDeployment.id == deployment_id
        ).first()
