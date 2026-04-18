"""Graph builder for talent intelligence skill visualization.

Uses NetworkX to build a directed graph of matched/missing/bonus skills,
then renders with Pyvis for interactive exploration.
"""

import os
import re

import networkx as nx
from pyvis.network import Network

from dummy_match import dummy_perfect, dummy_weak, dummy_hidden, job_title

try:
    from talent_core.person1.utils import skill_similarity
except Exception:
    skill_similarity = None


def _build_skill_graph(match_result, job_title):
    """Build a role-centric NetworkX graph from match results."""
    graph = nx.DiGraph()

    fit_score = match_result.get("fit_score", 0)
    matched_skills = match_result.get("matched_skills", [])
    missing_skills = match_result.get("missing_skills", [])
    bonus_skills = match_result.get("bonus_skills", [])
    skill_scores = match_result.get("skill_scores", {})
    github_score = match_result.get("breakdown", {}).get("github_score", "N/A")

    matched_set = set(matched_skills)
    missing_set = set(missing_skills)
    bonus_set = set(bonus_skills)
    has_skill_scores = isinstance(skill_scores, dict)

    def _score_for_tooltip(skill: str):
        if not has_skill_scores:
            return None
        try:
            raw = skill_scores.get(skill, None)
            if raw is None:
                return None
            return float(raw)
        except Exception:
            return None

    # Center node: role target from Person 3 specification.
    role_label = f"{job_title}\n{fit_score}/100"
    matched_preview = ", ".join(matched_skills[:8]) if matched_skills else "None"
    if len(matched_skills) > 8:
        matched_preview += ", ..."
    graph.add_node(
        "ROLE",
        label=role_label,
        title=(
            f"🎯 {job_title}\n"
            f"Fit Score: {fit_score}/100\n"
            f"GitHub Score: {github_score}\n"
            f"Matched Skills ({len(matched_skills)}): {matched_preview}"
        ),
        color={"background": "#7F77DD", "border": "#7F77DD"},
        size=55,
        shape="star",
        font={"size": 20, "color": "white", "bold": True},
        borderWidth=2,
        borderWidthSelected=4,
        shadow=True,
    )

    node_lookup = {}

    for skill in matched_skills:
        node_id = f"matched_{skill}"
        node_lookup[skill] = node_id
        role_score = _score_for_tooltip(skill)
        score_text = f"{role_score:.2f}" if role_score is not None else "N/A"
        graph.add_node(
            node_id,
            label=skill,
            title=(
                f"✅ {skill}\n"
                f"Candidate match score: {score_text}\n"
                "Status: Matched ✓"
            ),
            color={"background": "#1D9E75", "border": "#1D9E75"},
            size=38,
            font={"size": 13, "color": "white"},
            borderWidth=2,
            borderWidthSelected=4,
            shadow=True,
        )
        graph.add_edge(
            "ROLE",
            node_id,
            color="#1D9E75",
            width=3,
            dashes=False,
            label="matched",
        )

    for skill in missing_skills:
        node_id = f"missing_{skill}"
        node_lookup[skill] = node_id
        role_score = _score_for_tooltip(skill)
        score_text = f"{role_score:.2f}" if role_score is not None else "N/A"
        graph.add_node(
            node_id,
            label=skill,
            title=(
                f"❌ {skill}\n"
                f"Best candidate match: {score_text}\n"
                "Status: GAP — candidate lacks this skill"
            ),
            color={"background": "#E24B4A", "border": "#E24B4A"},
            size=30,
            font={"size": 13, "color": "white"},
            borderWidth=2,
        )
        graph.add_edge(
            "ROLE",
            node_id,
            color="#E24B4A",
            width=2,
            dashes=True,
            label="gap",
        )

    for skill in bonus_skills:
        node_id = f"bonus_{skill}"
        node_lookup[skill] = node_id
        graph.add_node(
            node_id,
            label=skill,
            title=(
                f"⭐ {skill}\n"
                "Status: Bonus — extra value beyond requirements"
            ),
            color={"background": "#378ADD", "border": "#378ADD"},
            size=28,
            font={"size": 12, "color": "white"},
            borderWidth=2,
        )
        graph.add_edge(
            "ROLE",
            node_id,
            color="#378ADD",
            width=1,
            dashes=False,
            label="bonus",
        )

    # Bonus: semantic links from Person 1 similarity model.
    if skill_similarity is not None:
        all_skills = list(node_lookup.keys())
        for i, skill_a in enumerate(all_skills):
            for skill_b in all_skills[i + 1 :]:
                # Skip edges between two gap skills and only connect pairs where
                # at least one side is matched or bonus.
                if skill_a in missing_set and skill_b in missing_set:
                    continue
                if not ((skill_a in matched_set or skill_a in bonus_set) or (skill_b in matched_set or skill_b in bonus_set)):
                    continue
                try:
                    sim = float(skill_similarity(skill_a, skill_b))
                except Exception:
                    continue
                if sim >= 0.7:
                    graph.add_edge(
                        node_lookup[skill_a],
                        node_lookup[skill_b],
                        color="#808080",
                        width=round(sim * 3, 2),
                        title=f"semantic similarity: {sim:.2f}",
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
        badge_color = "#28a745"
        badge_text = "Strong Fit"
    elif fit_score >= 40:
        badge_color = "#f0a500"
        badge_text = "Moderate Fit"
    else:
        badge_color = "#dc3545"
        badge_text = "Weak Fit"

    # Custom CSS and HTML to inject
    custom_html = f"""
    <style>
        body {{
            background: #0d1117;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        #title-bar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 999;
            height: 44px;
            background: rgba(13,17,23,0.85);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid #30363d;
            color: white;
            padding: 0 14px;
            font-size: 15px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0;
            pointer-events: none;
        }}
        #score-badge {{
            background: {badge_color};
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 15px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        #legend-bar {{
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 999;
            height: 36px;
            background: rgba(13,17,23,0.85);
            backdrop-filter: blur(8px);
            border-top: 1px solid #30363d;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ccc;
            font-size: 13px;
            gap: 20px;
        }}
        #mynetwork {{
            padding-top: 0 !important;
        }}
    </style>
    <div id="title-bar">
        <span>Talent Intelligence — Skill Graph</span>
        <div id="score-badge">🎯 {fit_score}/100 — {badge_text}</div>
    </div>
    <div id="legend-bar">
        <span>🟢 Matched</span>
        <span>🔴 Gap</span>
        <span>🔵 Bonus</span>
        <span>⭐ Role</span>
    </div>
    """

    # Ensure body fills viewport without extra scroll/margins.
    html_content = re.sub(
        r"<body[^>]*>",
        '<body style="margin:0; padding:0; overflow:hidden;">',
        html_content,
        count=1,
    )

    # Insert custom HTML before </body>
    html_content = html_content.replace("</body>", custom_html + "</body>")

    # Adjust the graph container div to have the proper height
    html_content = re.sub(
        r'<div id="mynetwork"[^>]*>',
        '<div id="mynetwork" style="width: 100%; height: calc(100vh - 60px); min-height: 500px;">',
        html_content,
        count=1,
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
        height="100vh",
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
                "solver": "barnesHut",
                "barnesHut": {
                    "gravitationalConstant": -12000,
                    "centralGravity": 0.1,
                    "springLength": 200,
                    "springConstant": 0.04,
                    "damping": 0.15,
                    "avoidOverlap": 0.2
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


def build_skill_graph(match_result, job_title, output_dir="graph_output"):
    """Backward-compatible graph API expected by verification scripts.

    Saves graph_output/skill_graph.html and returns analytics.
    """
    output_file = os.path.join(output_dir, "skill_graph.html")
    _, analytics = render_match_graph(
        match_result,
        candidate_name="skill_graph",
        job_title=job_title,
        output_dir=output_dir,
        scenario_type=None,
    )

    generated_file = os.path.join(output_dir, "skill_graph_graph.html")
    if os.path.exists(generated_file):
        os.replace(generated_file, output_file)

    return analytics


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
