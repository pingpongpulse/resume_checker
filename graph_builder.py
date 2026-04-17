"""Graph builder for talent intelligence skill visualization.

Uses NetworkX to build a directed graph of matched/missing/bonus skills,
then renders with Pyvis for interactive exploration.
"""

import os
import re

import networkx as nx
from pyvis.network import Network

from dummy_match import dummy_perfect, dummy_weak, dummy_hidden, job_title


def _build_skill_graph(match_result, job_title):
    """Build a premium NetworkX graph with visual hierarchy and neon styling."""
    graph = nx.DiGraph()

    fit_score = match_result.get("fit_score", 0)
    matched_skills = match_result.get("matched_skills", [])
    missing_skills = match_result.get("missing_skills", [])
    bonus_skills = match_result.get("bonus_skills", [])

    # Determine score-based color for connections and theme
    if fit_score >= 70:
        accent_color = "#00FF88"  # neon green
        accent_dim = "#1D9E75"
    elif fit_score >= 40:
        accent_color = "#FFD700"  # gold
        accent_dim = "#CC7700"
    else:
        accent_color = "#FF4D4D"  # neon red
        accent_dim = "#CC0000"

    # Center node: DOMINANT hero node (star, large, glowing)
    role_label = f"{job_title}\n{fit_score}/100"
    graph.add_node(
        "ROLE",
        label=role_label,
        title=f"🎯 {job_title} — Fit Score: {fit_score}/100",
        color={"background": "#7F77DD", "border": accent_color},
        size=60,
        shape="star",
        font={"size": 22, "color": "white", "bold": True},
        borderWidth=3,
    )

    # Matched skills (neon green with glow): size increases with index
    for idx, skill in enumerate(matched_skills):
        node_size = 30 + (idx * 2)
        graph.add_node(
            f"matched_{skill}",
            label=skill,
            title=f"✅ {skill} — Candidate has this",
            color={"background": accent_dim, "border": "#00FFAA"},
            size=node_size,
            font={"size": 13, "color": "white"},
            borderWidth=2,
        )
        # Strong solid edges to matched skills
        graph.add_edge(
            "ROLE",
            f"matched_{skill}",
            color=accent_color,
            width=3,
            dashes=False,
        )

    # Missing skills (neon red with dashed): uniform size
    for skill in missing_skills:
        graph.add_node(
            f"missing_{skill}",
            label=skill,
            title=f"❌ {skill} — Gap to fill",
            color={"background": "#CC0000", "border": "#FF4D4D"},
            size=22,
            font={"size": 13, "color": "white"},
            borderWidth=2,
        )
        # Weaker dashed edges to missing skills
        graph.add_edge(
            "ROLE",
            f"missing_{skill}",
            color="#FF4D4D",
            width=2,
            dashes=True,
        )

    # Bonus skills (neon blue): smaller size
    for skill in bonus_skills:
        graph.add_node(
            f"bonus_{skill}",
            label=skill,
            title=f"⭐ {skill} — Extra value",
            color={"background": "#0066FF", "border": "#4DA6FF"},
            size=18,
            font={"size": 12, "color": "white"},
            borderWidth=2,
        )
        graph.add_edge(
            "ROLE",
            f"bonus_{skill}",
            color="#4DA6FF",
            width=1.5,
            dashes=False,
        )

    # Add glowing similarity edges between matched skills (width based on importance)
    all_matched = matched_skills
    for i, skill1 in enumerate(all_matched[:4]):
        for j, skill2 in enumerate(all_matched[i + 1 : min(i + 3, len(all_matched))]):
            node1 = f"matched_{skill1}"
            node2 = f"matched_{skill2}"
            # Similarity width: closer skills get thicker edges
            similarity_width = max(2 - (j * 0.5), 0.5)
            graph.add_edge(
                node1,
                node2,
                color="#888888",
                width=similarity_width,
                hidden=False,
            )

    return graph


def get_graph_analytics(match_result: dict) -> dict:
    """Compute analytics from match_result without rendering graph.
    
    Fast computation for Streamlit UI display without full graph re-render.
    """
    matched = match_result.get("matched_skills", [])
    missing = match_result.get("missing_skills", [])
    bonus = match_result.get("bonus_skills", [])
    total = len(matched) + len(missing)
    
    return {
        "match_percent": round(len(matched) / total * 100) if total > 0 else 0,
        "matched_count": len(matched),
        "missing_count": len(missing),
        "bonus_count": len(bonus),
        "top_strength": matched[0] if matched else "None",
        "top_gap": missing[0] if missing else "None",
        "total_skills_evaluated": total,
    }


def _inject_html_styling(html_file_path, fit_score):
    """Inject custom CSS and title/badge into HTML file."""
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Determine badge color based on fit_score
    if fit_score >= 70:
        badge_color = "#28a745"  # green
        badge_text = "Strong Fit"
    elif fit_score >= 40:
        badge_color = "#ffc107"  # yellow
        badge_text = "Moderate Fit"
    else:
        badge_color = "#dc3545"  # red
        badge_text = "Weak Fit"

    # Custom CSS and HTML to inject
    custom_html = f"""
    <style>
        body {{
            background: #0d1117;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        #title-bar {{
            background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            color: white;
            padding: 16px 24px;
            font-size: 20px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0;
        }}
        #score-badge {{
            background: {badge_color};
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        #score-badge::before {{
            content: "📊";
        }}
        #graph-container {{
            position: relative;
            width: 100%;
            height: calc(100vh - 60px);
        }}
    </style>
    <div id="title-bar">
        <span>🧠 Talent Intelligence — Skill Graph</span>
        <div id="score-badge">{fit_score}/100 — {badge_text}</div>
    </div>
    <div id="graph-container">
    """

    # Insert custom HTML before </body>
    html_content = html_content.replace("</body>", custom_html + "</body>")

    # Adjust the graph container div to have the proper height
    html_content = re.sub(
        r'<div id="mynetwork"[^>]*>',
        '<div id="mynetwork" style="width: 100%; height: 100%;">',
        html_content,
    )

    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def render_match_graph(match_result, candidate_name, job_title, output_dir="graph_output", scenario_type=None):
    """Render a match result as an interactive skill graph.

    Args:
        match_result: dict with fit_score, matched_skills, missing_skills, etc.
        candidate_name: str for identification
        job_title: str role being matched
        output_dir: str directory to save HTML (default: "graph_output")
        scenario_type: str one of "perfect", "weak", "hidden" for standard naming

    Returns:
        tuple: (path_to_saved_html_file, analytics_dict)
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate output filename
    if scenario_type:
        output_file = os.path.join(output_dir, f"skill_graph_{scenario_type}.html")
    else:
        output_file = os.path.join(output_dir, f"{candidate_name}_graph.html")

    # Compute analytics for downstream UI use
    analytics = get_graph_analytics(match_result)

    # Build graph
    graph = _build_skill_graph(match_result, job_title)

    # Create premium Pyvis network with enhanced styling
    net = Network(
        directed=True,
        height="700px",
        width="100%",
        bgcolor="#0d1117",
        font_color="white",
        notebook=False,
    )
    net.from_nx(graph)

    # Configure physics for beautiful spreading and stabilization
    net.toggle_physics(True)

    # Set comprehensive physics and interaction options for premium feel
    net.set_options(
        """
        {
            "physics": {
                "enabled": true,
                "forceAtlas2Based": {
                    "gravitationalConstant": -26,
                    "centralGravity": 0.3,
                    "springLength": 200,
                    "springConstant": 0.05,
                    "dissuadeHubs": true,
                    "overlap": 0.5
                },
                "maxVelocity": 50,
                "stabilization": {
                    "enabled": true,
                    "iterations": 200,
                    "fit": true
                },
                "timestep": 0.35,
                "adaptiveTimestep": true
            },
            "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true,
                "zoomView": true
            }
        }
        """
    )

    # Write HTML directly
    net.write_html(output_file)

    # Post-process HTML to add custom styling
    fit_score = match_result.get("fit_score", 0)
    _inject_html_styling(output_file, fit_score)

    return output_file, analytics


if __name__ == "__main__":
    # Test with dummy scenarios
    print("Rendering skill graphs for dummy scenarios...\n")

    scenarios = [
        (dummy_perfect, "Aarav_Menon_perfect", "perfect"),
        (dummy_weak, "Riya_Sharma_weak", "weak"),
        (dummy_hidden, "Karan_Iqbal_hidden", "hidden"),
    ]

    print("="*70)
    for match_result, candidate_name, scenario_type in scenarios:
        output_path, analytics = render_match_graph(
            match_result,
            candidate_name,
            job_title,
            scenario_type=scenario_type,
        )
        fit_score = match_result.get("fit_score", 0)
        print(f"\n✓ {scenario_type.upper()} Scenario: {candidate_name}")
        print(f"  HTML File: {output_path}")
        print(f"  Fit Score: {fit_score}/100")
        print(f"  Analytics:")
        print(f"    - Match Percent: {analytics['match_percent']}%")
        print(f"    - Matched Skills: {analytics['matched_count']}/{analytics['total_skills_evaluated']}")
        print(f"    - Missing Skills: {analytics['missing_count']}")
        print(f"    - Bonus Skills: {analytics['bonus_count']}")
        print(f"    - Top Strength: {analytics['top_strength']}")
        print(f"    - Top Gap: {analytics['top_gap']}")
    print("\n" + "="*70)
    print("\n✓ All graphs generated successfully in graph_output/ folder.")
    print("  Open the HTML files in your browser to explore the interactive visualizations.")
