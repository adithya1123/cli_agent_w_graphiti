# Contracts: visualizer
_Last updated: 2026-04-25_
_Covers: `src/visualizer.py`_

---

## GraphVisualizer.__init__

**Summary**: Opens a direct Neo4j driver connection (independent of Graphiti).
**File**: `src/visualizer.py:19`

**Side effects**: Creates `neo4j.GraphDatabase.driver` — must call `close()` to release it.

**Failure modes**: Raises immediately if Neo4j is unreachable — no lazy connection.

---

## GraphVisualizer.visualize_user_graph

**Summary**: Fetches user's graph data, renders HTML visualization, opens in browser.
**File**: `src/visualizer.py:53`

**Returns**: Path to the generated HTML file, or `None` if no data or on error.

**Non-obvious behavior**:
- Prints `"No conversation data found for user '...'"` and returns `None` if no Episodic nodes — does not raise
- HTML file is written to `tempfile.gettempdir()/agent_visualizations/graph_{user_id}_{timestamp}.html`
- Opens browser via `webbrowser.open()` by default — pass `open_browser=False` to suppress

**Failure modes**: Exceptions from Neo4j or file I/O are caught, logged, and printed — returns `None`.

---

## GraphVisualizer._fetch_graph_data

**Summary**: Cypher query to fetch Episodic nodes + MENTIONS relationships + Entity nodes for a user.
**File**: `src/visualizer.py:109`

**Non-obvious behavior**:
- Query uses `OPTIONAL MATCH` for entities — episodes without any entities are still returned
- Limited to 500 records (`LIMIT 500`) — large graphs are silently truncated
- Uses `ep.valid_at` as the timestamp property (Graphiti schema) — falls back to `created_at` if absent
- Does NOT fetch `:RELATES_TO` (entity-to-entity) edges — only `:MENTIONS`

**Returns**: `(nodes_list, edges_list, stats_dict)`

---

## GraphVisualizer.close

**Summary**: Closes the Neo4j driver connection.
**File**: `src/visualizer.py:47`

**Invariants**: Must be called after use. In `main.py`, called immediately after `visualize_user_graph()` returns.

→ See also: `03_narratives.md#visualizer`, `01_hazards.md#visualizer-uses-a-separate-direct-neo4j-driver`
