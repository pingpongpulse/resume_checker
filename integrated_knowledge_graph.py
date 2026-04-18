import sys
import json
import re
import requests
import time
import base64
import pdfplumber
import networkx as nx
from pyvis.network import Network
from pathlib import Path

# Add project root to path for local talent_ai module import
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from talent_ai.person1.resume_parser import parse_resume_text
from talent_ai.person1.utils import skill_similarity

BASE_URL = "https://api.github.com/users/"

JOB_DEF = {
    "title": "ML Engineer",
    "required_skills": ["python", "django", "kubernetes", "tensorflow", "fastapi", "docker", "react"]
}

# -------------------- GitHub Logic --------------------

def get_readme(username, repo):
    try:
        url = f"https://api.github.com/repos/{username}/{repo}/readme"
        res = requests.get(url)
        if res.status_code != 200:
            return ""
        data = res.json()
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return content[:2000]
    except:
        return ""

def repo_skill_score(readme_text, required_skills):
    text = readme_text.lower()
    score = 0
    matched = []
    for skill in required_skills:
        if skill.lower() in text:
            score += 1
            if skill.lower() not in matched:
                matched.append(skill.lower())
    return score, matched

def get_github_data(username, required_skills):
    try:
        user_url = BASE_URL + username
        repos_url = user_url + "/repos?per_page=30&sort=updated"
        res = requests.get(repos_url)
        
        if res.status_code == 403 or res.status_code == 429:
            print(f"\\n[WARNING] GitHub API Rate Limit exceeded! You cannot fetch more data for an hour.\\n")
            return {"github_languages": [], "repo_scores": []}
            
        repos = res.json()
        if not isinstance(repos, list):
            return {"github_languages": [], "repo_scores": []}

        repo_names = []
        languages = {}
        repo_scores = []
        
        for i, repo in enumerate(repos):
            if not isinstance(repo, dict) or "name" not in repo:
                continue
            repo_names.append(repo["name"])
            
            # Use primary language from repo dict to save API calls
            primary_lang = repo.get("language")
            if primary_lang:
                languages[primary_lang.lower()] = languages.get(primary_lang.lower(), 0) + 1
            
            # Only fetch ReadMe for top 3 recently updated repos to preserve rate limit!
            if i < 3:
                readme = get_readme(username, repo["name"])
                score, matched = repo_skill_score(readme, required_skills)

                repo_scores.append({
                    "name": repo["name"],
                    "score": score,
                    "matched": matched,
                    "stars": repo.get("stargazers_count", 0)
                })

        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        top_languages = [lang for lang, _ in sorted_langs[:5]]

        return {
            "github_languages": top_languages,
            "repo_scores": repo_scores
        }
    except Exception as e:
        print("GitHub Error:", e)
        return {"github_languages": [], "repo_scores": []}

def extract_github_username(raw_link):
    match = re.search(r'github\.com/([A-Za-z0-9_.\-]+)', raw_link, re.I)
    return match.group(1) if match else raw_link.strip("/")

# -------------------- Match Tracking Logic --------------------

def compute_match_result(candidate_skills, required_skills):
    matched_skills = []
    missing_skills = []
    bonus_skills = []
    matched_details = {}
    
    used_candidate_skills = set()
    
    for req_skill in required_skills:
        best_match = None
        best_sim = 0
        for cand_skill in candidate_skills:
            try:
                sim = skill_similarity(req_skill, cand_skill)
                if sim > best_sim:
                    best_sim = sim
                    best_match = cand_skill
            except Exception:
                pass
                
        if best_sim >= 0.75 and best_match is not None:
            matched_skills.append(req_skill)
            used_candidate_skills.add(best_match)
            matched_details[req_skill] = (best_match, best_sim)
        else:
            missing_skills.append(req_skill)
            
    for cand_skill in candidate_skills:
        if cand_skill not in used_candidate_skills:
            if len(cand_skill) > 2 and len(cand_skill) < 30:
                bonus_skills.append(cand_skill)
                
    # Limit bonus skills, picking strongest single words etc or just first 10
    bonus_skills = list(set(bonus_skills))[:8]
    
    return {
        "matched_skills": list(set(matched_skills)),
        "missing_skills": list(set(missing_skills)),
        "bonus_skills": bonus_skills,
        "matched_details": matched_details
    }

# -------------------- Graph Visualization --------------------

def build_graph(job, match_result):
    G = nx.Graph()
    role = job["title"]

    G.add_node(role, type="role")

    for skill in match_result["matched_skills"]:
        match_info = match_result["matched_details"].get(skill)
        match_str = f"Matched with: {match_info[0]} (sim: {match_info[1]:.2f})" if match_info else "Matched Skill"
        G.add_node(skill, type="matched", hover_text=match_str)

    for skill in match_result["missing_skills"]:
        G.add_node(skill, type="missing")

    for skill in match_result["bonus_skills"]:
        G.add_node(skill, type="bonus")

    # Connect requirements to role
    for skill in job["required_skills"]:
        if skill in match_result["matched_skills"] or skill in match_result["missing_skills"]:
            G.add_edge(skill, role, label="required")

    # Instead of an N x N messy web, we use a Hub-and-Spoke model:
    # Connect each bonus skill only to the *most similar* required skill.
    for bonus in match_result["bonus_skills"]:
        best_req = None
        best_sim = 0
        for req in job["required_skills"]:
            try:
                sim = skill_similarity(bonus, req)
                if sim > best_sim:
                    best_sim = sim
                    best_req = req
            except Exception:
                pass
                
        if best_req and best_sim >= 0.35: # very low threshold just to anchor it to the graph
            G.add_edge(bonus, best_req, weight=best_sim, label="sim")
            # Set the hover text for the node
            G.nodes[bonus]["hover_text"] = f"Bonus Skill\nMost similar to: {best_req} (sim: {best_sim:.2f})"

    return G

def visualize_graph(G, output_file="integrated_knowledge_graph.html"):
    net = Network(height="800px", width="100%", bgcolor="#1a1a2e", font_color="white")

    for node, data in G.nodes(data=True):
        if data["type"] == "role":
            net.add_node(node, color="#00BFFF", size=45, title="Job Role")
        elif data["type"] == "matched":
            hover = data.get("hover_text", "Matched Skill")
            net.add_node(node, color="#2ecc71", size=30, title=hover)
        elif data["type"] == "missing":
            net.add_node(node, color="#e74c3c", size=30, title="Missing Skill")
        else:
            hover = data.get("hover_text", "Bonus Skill")
            net.add_node(node, color="#95a5a6", size=20, title=hover)

    for u, v, data in G.edges(data=True):
        weight = data.get("weight", 1.0)
        label = data.get("label", "")
        # Highlight required edges from role
        if label == "required":
            net.add_edge(u, v, title=label, color="#3498db", width=2)
        else:
            # Subtle low opacity edges for bonus similarity lines
            net.add_edge(u, v, title=f"sim: {weight:.2f}", value=weight, color="rgba(255,255,255,0.1)")

    # Manage physics perfectly for a hub-and-spoke star shape
    net.set_options('{"physics": {"barnesHut": {"springLength": 180, "springConstant": 0.04, "centralGravity": 0.3}}}')
    net.write_html(output_file)
    print(f"Graph written to {output_file}")


def main():
    # Attempt parsing default PDF, fallback to empty string if unable
    pdf_path = project_root / "P_Sai_Lekhya_Resume_compressed (1).pdf"
    
    print(f"Reading {pdf_path.name}...")
    full_text = ""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception as e:
        print(f"Could not read PDF ({e}). Will proceed with mostly blank.")

    # 1. Extract Candidate Profile via resume_checker's model
    print("Parsing resume text using `talent_ai.person1.resume_parser`...")
    candidate_profile = parse_resume_text(full_text)
    
    candidate_skills = list(candidate_profile.get("skills", []))
    print(f"Extracted skills from resume: {candidate_skills}")
    
    # 2. Retrieve GitHub Data
    gh_links = candidate_profile.get("links", {}).get("github")
    if gh_links:
        if isinstance(gh_links, list):
            gh_links = gh_links[0]
        
        username = extract_github_username(gh_links)
        print(f"Fetching GitHub data for: {username} (this may take a few seconds due to ratelimiting)")
        
        github_data = get_github_data(username, JOB_DEF["required_skills"])
        print(f"Top langs from GitHub: {github_data['github_languages']}")
        
        # Merge github languages into candidate skills
        candidate_skills.extend([lang.lower() for lang in github_data["github_languages"]])
    else:
        print("No GitHub link found. Skipping github fetch.")

    candidate_skills = list(set(candidate_skills))
    
    # 3. Compute matches considering talent_ai's w2v text similarity!
    print("Computing matches vs required job skills... (using `talent_ai.person1.utils`)")
    match_result = compute_match_result(candidate_skills, JOB_DEF["required_skills"])
    print(json.dumps(match_result, indent=2))

    # 4. Build and Visualize Knowledge Graph
    print("Building Knowledge Graph...")
    G = build_graph(JOB_DEF, match_result)
    
    output_html = "integrated_knowledge_graph.html"
    visualize_graph(G, output_html)
    print("Graph generation pipeline successfully completed!")

if __name__ == "__main__":
    main()
