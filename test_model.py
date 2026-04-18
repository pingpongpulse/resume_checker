from talent_core.person1.utils import skill_similarity

tests = [
    # HIGH
    ("flask", "django", "HIGH"),
    ("docker", "kubernetes", "HIGH"),
    ("react", "javascript", "HIGH"),

    # MEDIUM
    ("flask", "nodejs", "MEDIUM"),
    ("mongodb", "mysql", "MEDIUM"),

    # LOW
    ("html", "machine learning", "LOW"),
    ("css", "kubernetes", "LOW"),
    ("pytorch", "html", "LOW"),
]

def check(score, expected):
    if expected == "HIGH":
        return score > 0.6
    elif expected == "MEDIUM":
        return 0.3 <= score <= 0.6
    else:
        return score < 0.3

print("\n🔥 MODEL TEST RESULTS\n")

for a, b, expected in tests:
    score = skill_similarity(a, b)
    result = "PASS" if check(score, expected) else "FAIL"
    print(f"{a} vs {b} → {score:.3f} ({expected}) → {result}")