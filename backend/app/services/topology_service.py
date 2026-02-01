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

        # Find main router first
        main_router = self._find_main_router(routers)
        main_router_id = main_router.id if main_router else None

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

            # Determine node shape and size
            is_main = router.id == main_router_id
            shape = "star" if is_main else "dot"
            size = 35 if is_main else 20

            if not is_main and router.model:
                model_lower = router.model.lower()
                if "ccr" in model_lower:
                    shape = "diamond"
                    size = 25
                elif "crs" in model_lower:
                    shape = "square"
                    size = 22
                elif "cap" in model_lower or "wap" in model_lower:
                    shape = "triangle"
                    size = 22
                elif "sxt" in model_lower or "lhg" in model_lower:
                    shape = "triangleDown"
                    size = 22

            # Main router styling
            border_width = 3 if is_main else 2
            font_size = 14 if is_main else 12

            nodes.append({
                "id": router.id,
                "label": router.identity or router.ip,
                "title": self._build_node_tooltip(router, is_main),
                "ip": router.ip,
                "model": router.model,
                "version": router.ros_version,
                "status": status,
                "color": {"background": color, "border": "#000" if is_main else color},
                "shape": shape,
                "size": size,
                "borderWidth": border_width,
                "font": {"size": font_size, "bold": is_main}
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

    def _build_node_tooltip(self, router: Router, is_main: bool = False) -> str:
        """Build HTML tooltip for a node"""
        role = "⭐ Edge Router (Gateway)" if is_main else "Router"
        lines = [
            f"<b>{router.identity or 'Unknown'}</b>",
            f"Role: {role}",
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
        """Discover network edges from router neighbors or infer from network"""
        edges = []
        seen_edges = set()

        # Build IP to router ID map
        ip_to_id = {r.ip: r.id for r in routers}
        id_to_router = {r.id: r for r in routers}

        # Find the main/edge router (gateway)
        main_router = self._find_main_router(routers)

        if main_router and main_router.neighbors:
            # Only show connections FROM the main router
            # These are the real physical connections
            for neighbor in main_router.neighbors:
                neighbor_ip = neighbor.get("address")
                if neighbor_ip and neighbor_ip in ip_to_id:
                    neighbor_id = ip_to_id[neighbor_ip]
                    neighbor_router = id_to_router.get(neighbor_id)

                    edge_key = tuple(sorted([main_router.id, neighbor_id]))
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)

                        # Clean up interface name for display
                        interface = neighbor.get("interface", "")
                        port_name = interface.split(",")[0] if interface else ""

                        # Determine edge style based on device type
                        color = "#6c757d"
                        dashes = False
                        width = 2

                        if neighbor_router and neighbor_router.model:
                            model_lower = neighbor_router.model.lower()
                            if "sxt" in model_lower or "lhg" in model_lower:
                                dashes = True
                                color = "#17a2b8"  # cyan for wireless
                            elif "cap" in model_lower or "wap" in model_lower:
                                color = "#28a745"  # green for APs

                        neighbor_name = neighbor.get('identity') or neighbor_ip

                        edges.append({
                            "from": main_router.id,
                            "to": neighbor_id,
                            "label": port_name,
                            "title": f"{main_router.identity} [{port_name}] → {neighbor_name}",
                            "font": {"size": 11, "align": "horizontal", "strokeWidth": 3, "strokeColor": "#ffffff"},
                            "width": width,
                            "dashes": dashes,
                            "color": {"color": color, "opacity": 0.9},
                            "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}}
                        })

        # If no edges found from main router, try inferred topology
        if not edges:
            edges = self._infer_topology(routers)

        return edges

    def _find_main_router(self, routers: List[Router]) -> Optional[Router]:
        """Find the main/edge router (gateway)"""
        # Look for keywords in identity
        keywords = ['glowny', 'main', 'core', 'gateway', 'edge', 'brzegowy', 'router']

        for router in routers:
            if router.identity:
                identity_lower = router.identity.lower()
                if any(kw in identity_lower for kw in keywords):
                    return router

        # Fallback: router with lowest IP (usually .1 or .2)
        online_routers = [r for r in routers if r.is_online]
        if online_routers:
            return min(online_routers, key=lambda r: tuple(map(int, r.ip.split('.'))))

        return routers[0] if routers else None

    def _infer_topology(self, routers: List[Router]) -> List[Dict[str, Any]]:
        """Infer network topology when no neighbor data available"""
        edges = []
        seen_edges = set()

        if len(routers) < 2:
            return edges

        # Find the main router
        main_router = self._find_main_router(routers)
        if not main_router:
            main_router = routers[0]

        # Create star topology with main router as hub
        for router in routers:
            if router.id == main_router.id:
                continue

            edge_key = tuple(sorted([main_router.id, router.id]))
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)

                # Determine edge style based on device type
                width = 2
                color = "#6c757d"
                dashes = False

                if router.model:
                    model_lower = router.model.lower()
                    if "sxt" in model_lower or "lhg" in model_lower:
                        # Wireless link
                        dashes = True
                        color = "#17a2b8"
                    elif "cap" in model_lower or "wap" in model_lower:
                        # AP connection
                        color = "#28a745"

                edge = {
                    "from": main_router.id,
                    "to": router.id,
                    "title": "Inferred connection",
                    "width": width,
                    "color": {"color": color, "opacity": 0.6},
                }
                if dashes:
                    edge["dashes"] = True

                edges.append(edge)

        return edges

    async def refresh_neighbors(self, router_id: int) -> Dict[str, Any]:
        """Fetch fresh neighbor data from a router"""
        router = self.db.query(Router).filter(Router.id == router_id).first()
        if not router:
            return {"error": "Router not found"}

        if not router.is_online:
            return {"error": "Router is offline"}

        neighbors = []
        client = None

        # Try different connection methods
        connection_attempts = [
            {"port": 443, "use_ssl": True},   # HTTPS on 443
            {"port": 80, "use_ssl": False},   # HTTP on 80
        ]

        for attempt in connection_attempts:
            try:
                client = RouterOSClient(
                    host=router.ip,
                    username=router.username,
                    password=router.password,
                    port=attempt["port"],
                    use_ssl=attempt["use_ssl"],
                    timeout=10
                )

                if client.connect():
                    logger.info(f"Connected to {router.ip} on port {attempt['port']}")

                    # Get IP neighbors
                    response = client.get("/ip/neighbor")
                    if response.success and response.data:
                        for n in response.data:
                            neighbors.append({
                                "address": n.get("address"),
                                "interface": n.get("interface"),
                                "mac": n.get("mac-address"),
                                "identity": n.get("identity"),
                                "platform": n.get("platform"),
                                "version": n.get("version"),
                                "source": "ip/neighbor"
                            })
                        logger.info(f"Found {len(neighbors)} neighbors on {router.ip}")

                    client.close()
                    break

            except Exception as e:
                logger.debug(f"Connection attempt to {router.ip}:{attempt['port']} failed: {e}")
                if client:
                    try:
                        client.close()
                    except:
                        pass

        # Update router with neighbor data
        router.neighbors = neighbors
        self.db.commit()

        return {
            "router_id": router_id,
            "neighbors": neighbors,
            "count": len(neighbors)
        }

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
