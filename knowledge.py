import networkx as nx
from pyvis.network import Network

candidate = {
    "skills": ["Python", "FastAPI", "Docker"]
}

job = {
    "title": "ML Engineer",
    "required_skills": ["Python", "Django", "Kubernetes"]
}

# Simulated match_result (from scorer)
match_result = {
    "matched_skills": ["Python"],
    "missing_skills": ["Django", "Kubernetes"],
    "bonus_skills": ["FastAPI", "Docker"]
}
# Dummy similarity function (replace with Word2Vec later)
def similarity(skill1, skill2):
    dummy_sim = {
        ("FastAPI", "Django"): 0.8,
        ("Docker", "Kubernetes"): 0.75,
        ("Python", "Django"): 0.6
    }
    return dummy_sim.get((skill1, skill2), dummy_sim.get((skill2, skill1), 0))


def build_graph(candidate, job, match_result):
    G = nx.Graph()

    role = job["title"]

    # -------- ADD ROLE NODE --------
    G.add_node(role, type="role")

    # -------- ADD SKILL NODES --------
    for skill in match_result["matched_skills"]:
        G.add_node(skill, type="matched")

    for skill in match_result["missing_skills"]:
        G.add_node(skill, type="missing")

    for skill in match_result["bonus_skills"]:
        G.add_node(skill, type="bonus")

    # -------- CONNECT TO ROLE --------
    for skill in job["required_skills"]:
        G.add_edge(skill, role, label="required")

    # -------- ADD SIMILARITY EDGES --------
    all_skills = (
        match_result["matched_skills"] +
        match_result["missing_skills"] +
        match_result["bonus_skills"]
    )

    for i in range(len(all_skills)):
        for j in range(i + 1, len(all_skills)):
            sim = similarity(all_skills[i], all_skills[j])
            if sim > 0.6:
                G.add_edge(all_skills[i], all_skills[j], weight=sim)

    return G


def visualize_graph(G):
    net = Network(height="600px", width="100%", bgcolor="#1a1a2e", font_color="white")

    for node, data in G.nodes(data=True):
        if data["type"] == "role":
            net.add_node(node, color="#00BFFF", size=40)

        elif data["type"] == "matched":
            net.add_node(node, color="green", size=30)

        elif data["type"] == "missing":
            net.add_node(node, color="red", size=30)

        else:
            net.add_node(node, color="gray", size=20)

    for u, v, data in G.edges(data=True):
        net.add_edge(u, v)

    net.write_html("graph.html")


# -------- RUN --------
G = build_graph(candidate, job, match_result)
visualize_graph(G)
