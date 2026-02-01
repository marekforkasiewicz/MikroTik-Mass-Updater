"""Topology service for network visualization"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from ..models.router import Router
from ..models.monitoring import HealthCheck
from .routeros_rest import RouterOSClient

logger = logging.getLogger(__name__)


class TopologyService:
    """Service for network topology discovery and visualization"""

    def __init__(self, db: Session):
        self.db = db

    def get_topology_map(self) -> Dict[str, Any]:
        """Get network topology data for visualization"""
        routers = self.db.query(Router).all()

        nodes = []
        edges = []
        router_map = {}  # Map IP to router for edge creation

        for router in routers:
            router_map[router.ip] = router

            # Determine node status/color
            status = "offline"
            color = "#dc3545"  # red

            if router.is_online:
                # Check latest health
                health = self.db.query(HealthCheck).filter(
                    HealthCheck.router_id == router.id
                ).order_by(HealthCheck.checked_at.desc()).first()

                if health:
                    if health.status == "ok":
                        status = "healthy"
                        color = "#198754"  # green
                    elif health.status == "warning":
                        status = "warning"
                        color = "#ffc107"  # yellow
                    elif health.status == "critical":
                        status = "critical"
                        color = "#dc3545"  # red
                    else:
                        status = "online"
                        color = "#0d6efd"  # blue
                else:
                    status = "online"
                    color = "#0d6efd"  # blue

            # Determine node shape based on model
            shape = "dot"
            if router.model:
                model_lower = router.model.lower()
                if "ccr" in model_lower:
                    shape = "diamond"  # Core router
                elif "crs" in model_lower:
                    shape = "square"  # Switch
                elif "cap" in model_lower or "wap" in model_lower:
                    shape = "triangle"  # AP
                else:
                    shape = "dot"  # Regular router

            nodes.append({
                "id": router.id,
                "label": router.identity or router.ip,
                "title": self._build_node_tooltip(router),
                "ip": router.ip,
                "model": router.model,
                "version": router.ros_version,
                "status": status,
                "color": color,
                "shape": shape,
                "size": 25 if shape == "diamond" else 20,
                "font": {"size": 12}
            })

        # Try to discover edges from neighbor data
        edges = self._discover_edges(routers)

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "online": sum(1 for n in nodes if n["status"] != "offline"),
                "offline": sum(1 for n in nodes if n["status"] == "offline"),
                "total_edges": len(edges)
            }
        }

    def _build_node_tooltip(self, router: Router) -> str:
        """Build HTML tooltip for a node"""
        lines = [
            f"<b>{router.identity or 'Unknown'}</b>",
            f"IP: {router.ip}",
        ]
        if router.model:
            lines.append(f"Model: {router.model}")
        if router.ros_version:
            lines.append(f"Version: {router.ros_version}")
        if router.uptime:
            lines.append(f"Uptime: {router.uptime}")
        lines.append(f"Status: {'Online' if router.is_online else 'Offline'}")

        return "<br>".join(lines)

    def _discover_edges(self, routers: List[Router]) -> List[Dict[str, Any]]:
        """Discover network edges from router neighbors"""
        edges = []
        seen_edges = set()

        # Build IP to router ID map
        ip_to_id = {r.ip: r.id for r in routers}

        for router in routers:
            if not router.is_online:
                continue

            # Check if router has neighbors info stored
            if router.neighbors:
                for neighbor in router.neighbors:
                    neighbor_ip = neighbor.get("address")
                    if neighbor_ip and neighbor_ip in ip_to_id:
                        neighbor_id = ip_to_id[neighbor_ip]

                        # Create unique edge key (sorted to avoid duplicates)
                        edge_key = tuple(sorted([router.id, neighbor_id]))
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges.append({
                                "from": router.id,
                                "to": neighbor_id,
                                "title": neighbor.get("interface", ""),
                                "width": 2,
                                "color": {"color": "#6c757d", "opacity": 0.8}
                            })

        return edges

    async def refresh_neighbors(self, router_id: int) -> Dict[str, Any]:
        """Fetch fresh neighbor data from a router"""
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return {"error": "Router not found"}

        if not router.is_online:
            return {"error": "Router is offline"}

        try:
            client = RouterOSClient(
                host=router.ip,
                username=router.username,
                password=router.password,
                port=router.rest_port or 443
            )

            neighbors = []

            # Get IP neighbors
            try:
                ip_neighbors = client.get("/ip/neighbor")
                for n in ip_neighbors:
                    neighbors.append({
                        "address": n.get("address"),
                        "interface": n.get("interface"),
                        "mac": n.get("mac-address"),
                        "identity": n.get("identity"),
                        "platform": n.get("platform"),
                        "version": n.get("version"),
                        "source": "ip/neighbor"
                    })
            except Exception as e:
                logger.warning(f"Failed to get IP neighbors from {router.ip}: {e}")

            # Update router with neighbor data
            router.neighbors = neighbors
            self.db.commit()

            return {
                "router_id": router_id,
                "neighbors": neighbors,
                "count": len(neighbors)
            }

        except Exception as e:
            logger.error(f"Failed to refresh neighbors for {router.ip}: {e}")
            return {"error": str(e)}

    async def refresh_all_neighbors(self) -> Dict[str, Any]:
        """Refresh neighbor data for all online routers"""
        routers = self.db.query(Router).filter(Router.is_online == True).all()

        results = {
            "success": 0,
            "failed": 0,
            "details": []
        }

        for router in routers:
            result = await self.refresh_neighbors(router.id)
            if "error" in result:
                results["failed"] += 1
            else:
                results["success"] += 1
            results["details"].append({
                "router_id": router.id,
                "ip": router.ip,
                "result": result
            })

        return results

    def get_router_neighbors(self, router_id: int) -> Dict[str, Any]:
        """Get stored neighbors for a specific router"""
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return {"error": "Router not found"}

        return {
            "router_id": router_id,
            "ip": router.ip,
            "identity": router.identity,
            "neighbors": router.neighbors or [],
            "count": len(router.neighbors) if router.neighbors else 0
        }

    def save_layout(self, layout: Dict[str, Any]) -> bool:
        """Save user-defined node positions"""
        # For now, we'll store layout in memory or a settings table
        # In production, this could be stored per-user
        return True

    def get_layout(self) -> Optional[Dict[str, Any]]:
        """Get saved node positions"""
        return None
