"""Graph visualization for per-user knowledge graphs in Neo4j"""

import webbrowser
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from neo4j import GraphDatabase
from src.config import Neo4jConfig
from src.logging_config import get_logger

logger = get_logger(__name__)


class GraphVisualizer:
    """Visualizes per-user knowledge graphs stored in Neo4j"""

    def __init__(self, neo4j_config: Optional[Neo4jConfig] = None):
        """Initialize visualizer with Neo4j connection config

        Args:
            neo4j_config: Neo4jConfig instance. If None, uses environment variables
        """
        if neo4j_config is None:
            neo4j_config = Neo4jConfig()

        self.config = neo4j_config
        self.driver = None
        self._connect()

    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.user, self.config.password)
            )
            # Verify connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.debug("Connected to Neo4j successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.debug("Neo4j connection closed")

    def visualize_user_graph(
        self,
        user_id: str,
        days_back: Optional[int] = None,
        output_file: Optional[str] = None,
        open_browser: bool = True
    ) -> str:
        """Generate and display interactive visualization of user's knowledge graph

        Args:
            user_id: User ID (matches group_id in Neo4j)
            days_back: Show last N days of data. None = all time
            output_file: Path to save HTML. If None, uses temp file
            open_browser: Whether to automatically open in browser

        Returns:
            Path to generated HTML file
        """
        try:
            # Fetch graph data
            logger.info(f"Fetching graph data for user: {user_id}")
            nodes, edges, stats = self._fetch_graph_data(user_id, days_back)

            if not nodes:
                print(f"\n⚠️  No conversation data found for user '{user_id}'")
                print("   Chat with the agent first to build the knowledge graph.")
                return None

            # Render visualization
            logger.info(f"Rendering visualization ({len(nodes)} nodes, {len(edges)} edges)")
            output_path = self._render_visualization(
                nodes, edges, stats, user_id, days_back, output_file
            )

            # Display info
            time_range = f"last {days_back} days" if days_back else "all time"
            print(f"\n✅ Graph visualization generated")
            print(f"   User: {user_id}")
            print(f"   Time range: {time_range}")
            print(f"   Nodes: {stats['node_count']} | Episodes: {stats['episode_count']} | Relationships: {len(edges)}")
            print(f"   File: {output_path}")

            # Open in browser
            if open_browser:
                webbrowser.open(f"file://{Path(output_path).absolute()}")
                print("   Opening in browser...\n")
            else:
                print(f"\n   Open the file to view: {output_path}\n")

            return output_path

        except Exception as e:
            logger.error(f"Error visualizing graph: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return None

    def _fetch_graph_data(
        self,
        user_id: str,
        days_back: Optional[int] = None
    ) -> tuple[List[Dict], List[Dict], Dict[str, Any]]:
        """Fetch graph data from Neo4j for a specific user

        Returns:
            Tuple of (nodes, edges, stats_dict)
        """
        try:
            with self.driver.session() as session:
                # Build Cypher query with optional time filter
                time_filter = ""
                params = {"user_id": user_id}

                if days_back:
                    time_filter = f"AND ep.valid_at >= datetime() - duration({{days: {days_back}}})"

                # Query episodes (Episodic nodes) and their relationships
                # Graphiti schema: :Episodic nodes, :MENTIONS/:RELATES_TO relationships
                query = f"""
                MATCH (ep:Episodic)
                WHERE ep.group_id = $user_id {time_filter}
                OPTIONAL MATCH (ep)-[r:MENTIONS]-(entity:Entity)
                RETURN ep, r, entity
                ORDER BY ep.valid_at DESC
                LIMIT 500
                """

                logger.debug(f"Executing query with user_id={user_id}, days_back={days_back}")
                result = session.run(query, params)

                # Process results into nodes and edges
                nodes_dict = {}  # id -> node_data
                edges = []
                episodes = []

                for record in result:
                    ep = record["ep"]
                    rel = record["r"]
                    entity = record["entity"]

                    # Add episode (Episodic) node
                    ep_id = ep.id
                    if ep_id not in nodes_dict:
                        # Get valid_at timestamp (Graphiti uses valid_at, not reference_time)
                        valid_at = ep.get('valid_at', ep.get('created_at', 'unknown'))
                        if valid_at:
                            timestamp_str = str(valid_at)[:10]
                        else:
                            timestamp_str = 'unknown'

                        nodes_dict[ep_id] = {
                            "id": ep_id,
                            "label": f"Episode\n{timestamp_str}",
                            "title": ep.get("content", ep.get("name", ""))[:200],
                            "type": "episode",
                            "properties": dict(ep)
                        }
                        episodes.append(ep)

                    # Add entity node and relationship
                    if entity:
                        entity_id = entity.id
                        if entity_id not in nodes_dict:
                            entity_labels = list(entity.labels) if hasattr(entity, 'labels') else ['Entity']
                            nodes_dict[entity_id] = {
                                "id": entity_id,
                                "label": entity.get("name", str(entity_id))[:30],
                                "title": dict(entity),
                                "type": entity_labels[0] if entity_labels else "Entity",
                                "properties": dict(entity)
                            }

                        # Add edge
                        if rel:
                            edges.append({
                                "from": ep_id,
                                "to": entity_id,
                                "label": rel.type,
                                "title": rel.type
                            })

                nodes = list(nodes_dict.values())

                # Calculate statistics
                latest_ep_time = None
                if episodes:
                    latest_ep_time = episodes[0].get("valid_at", episodes[0].get("created_at"))

                stats = {
                    "node_count": len(nodes),
                    "episode_count": len(episodes),
                    "entity_count": len(nodes) - len(episodes),
                    "edge_count": len(edges),
                    "time_range": f"last {days_back} days" if days_back else "all time",
                    "latest_episode": latest_ep_time
                }

                logger.info(f"Fetched {len(nodes)} nodes, {len(edges)} edges for user {user_id}")
                return nodes, edges, stats

        except Exception as e:
            logger.error(f"Error fetching graph data: {e}", exc_info=True)
            raise

    def _render_visualization(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        stats: Dict[str, Any],
        user_id: str,
        days_back: Optional[int],
        output_file: Optional[str]
    ) -> str:
        """Render nodes and edges as interactive HTML visualization

        Returns:
            Path to generated HTML file
        """
        # Create output file path
        if output_file is None:
            temp_dir = Path(tempfile.gettempdir()) / "agent_visualizations"
            temp_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = temp_dir / f"graph_{user_id}_{timestamp}.html"
        else:
            output_file = Path(output_file)

        # Create HTML content
        html_content = self._create_html_visualization(
            nodes, edges, stats, user_id, days_back
        )

        # Write HTML file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Visualization saved to {output_file}")
        return str(output_file)

    def _create_html_visualization(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        stats: Dict[str, Any],
        user_id: str,
        days_back: Optional[int]
    ) -> str:
        """Create interactive HTML visualization using vis.js

        Uses vis.js library (CDN) for interactive graph visualization
        """
        time_range_text = f"Last {days_back} days" if days_back else "All time"

        # Convert nodes and edges to JSON
        import json
        nodes_json = json.dumps([
            {
                "id": n["id"],
                "label": n["label"],
                "title": str(n["title"])[:200],
                "color": self._get_node_color(n["type"]),
                "shape": self._get_node_shape(n["type"])
            }
            for n in nodes
        ])

        edges_json = json.dumps([
            {
                "from": e["from"],
                "to": e["to"],
                "label": e.get("label", ""),
                "title": e.get("title", "")
            }
            for e in edges
        ])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Knowledge Graph - {user_id}</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }}
        #header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        #header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        #stats {{
            font-size: 14px;
            margin-top: 10px;
            opacity: 0.9;
        }}
        #network {{
            width: 100%;
            height: calc(100vh - 150px);
            border: 1px solid #ddd;
        }}
        #footer {{
            background: #f5f5f5;
            padding: 10px 20px;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #ddd;
        }}
        .legend {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }}
        .legend-circle {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>📊 Knowledge Graph Visualization</h1>
        <div id="stats">
            <strong>User:</strong> {user_id} |
            <strong>Time Range:</strong> {time_range_text} |
            <strong>Episodes:</strong> {stats['episode_count']} |
            <strong>Entities:</strong> {stats['entity_count']} |
            <strong>Relationships:</strong> {stats['edge_count']}
        </div>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-circle" style="background-color: #667eea;"></div>
                <span>Episodes</span>
            </div>
            <div class="legend-item">
                <div class="legend-circle" style="background-color: #764ba2;"></div>
                <span>Entities</span>
            </div>
        </div>
    </div>

    <div id="network"></div>

    <div id="footer">
        Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
        Drag to pan, scroll to zoom, click nodes for details
    </div>

    <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});

        var data = {{
            nodes: nodes,
            edges: edges
        }};

        var options = {{
            physics: {{
                enabled: true,
                stabilization: {{
                    iterations: 200
                }},
                forceAtlas2Based: {{
                    gravitationalConstant: -26,
                    centralGravity: 0.005,
                    springLength: 200,
                    springConstant: 0.08
                }},
                maxVelocity: 50,
                timestep: 0.35,
                solver: 'forceAtlas2Based'
            }},
            interaction: {{
                navigationButtons: true,
                keyboard: true,
                zoomView: true,
                dragView: true
            }},
            nodes: {{
                font: {{
                    size: 14
                }}
            }},
            edges: {{
                arrows: 'to',
                smooth: {{
                    type: 'continuous'
                }},
                color: {{
                    color: '#999999',
                    highlight: '#ff6b6b'
                }}
            }}
        }};

        var container = document.getElementById('network');
        var network = new vis.Network(container, data, options);

        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                console.log('Selected node:', node);
            }}
        }});
    </script>
</body>
</html>"""

        return html

    @staticmethod
    def _get_node_color(node_type: str) -> str:
        """Get color for node type"""
        colors = {
            "episode": "#667eea",
            "Entity": "#764ba2",
            "Person": "#f093fb",
            "Organization": "#4facfe",
            "Location": "#43e97b",
            "Event": "#fa709a"
        }
        return colors.get(node_type, "#999999")

    @staticmethod
    def _get_node_shape(node_type: str) -> str:
        """Get shape for node type"""
        shapes = {
            "episode": "box",
            "Entity": "dot",
            "Person": "diamond",
            "Organization": "ellipse",
            "Location": "triangle"
        }
        return shapes.get(node_type, "dot")

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's knowledge graph

        Returns:
            Dictionary with stats like episode_count, entity_count, etc.
        """
        try:
            with self.driver.session() as session:
                # Use correct Graphiti schema: :Episodic nodes
                query = """
                MATCH (ep:Episodic)
                WHERE ep.group_id = $user_id
                OPTIONAL MATCH (ep)-[r]-(entity:Entity)
                WITH COUNT(DISTINCT ep) as episode_count,
                     COUNT(DISTINCT entity) as entity_count,
                     COUNT(DISTINCT r) as rel_count
                RETURN episode_count, entity_count, rel_count
                """

                result = session.run(query, {"user_id": user_id}).single()

                if result:
                    return {
                        "episode_count": result["episode_count"],
                        "entity_count": result["entity_count"],
                        "relationship_count": result["rel_count"],
                        "user_id": user_id
                    }
                else:
                    return {
                        "episode_count": 0,
                        "entity_count": 0,
                        "relationship_count": 0,
                        "user_id": user_id
                    }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            raise
