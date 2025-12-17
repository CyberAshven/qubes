"""Analyze which Relationship fields are actually used vs. just serialized"""
import re
from pathlib import Path
from collections import defaultdict

# All fields in Relationship class
ALL_FIELDS = [
    # Identity
    "public_key", "nft_address", "has_met", "first_contact_timestamp", "first_contact_block",

    # Interaction Stats
    "total_messages_sent", "total_messages_received", "total_collaborations",
    "average_response_time_seconds", "last_interaction_timestamp", "interaction_frequency_per_day",

    # Trust Metrics
    "reliability_score", "honesty_score", "expertise_scores", "responsiveness_score", "overall_trust_score",

    # Collaboration History
    "successful_joint_tasks", "failed_joint_tasks", "disputes_raised", "disputes_resolved", "multi_sig_agreements",

    # Reputation Signals
    "endorsements_given", "endorsements_received", "warnings_issued", "warnings_received", "third_party_reputation",

    # Economic
    "tokens_sent", "tokens_received", "transactions_completed", "payment_reliability",

    # Behavioral Patterns
    "communication_style", "preferred_topics", "time_zone", "active_hours", "quirks",

    # Security
    "authentication_failures", "suspicious_behavior_flags", "last_key_rotation", "compromise_alerts",

    # Social Dynamics
    "relationship_status", "relationship_progression", "is_best_friend", "friendship_anniversary",
    "friendship_level", "affection_level", "respect_level", "shared_experiences", "compatibility_score",

    # Memory Sharing
    "memory_sharing_permissions",

    # Notes
    "notes"
]

def find_field_usage(field_name):
    """Find all usages of a field in the codebase"""
    pattern = rf"\.{field_name}\b"

    # Files to search
    py_files = list(Path(".").rglob("*.py"))

    usages = []
    for py_file in py_files:
        # Skip test files and this script
        if "test_" in str(py_file) or "analyze_relationship_fields" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            matches = re.finditer(pattern, content)

            for match in matches:
                # Get line number
                line_num = content[:match.start()].count('\n') + 1

                # Get the line content
                lines = content.split('\n')
                line_content = lines[line_num - 1].strip()

                # Categorize usage
                if "to_dict" in line_content or "from_dict" in line_content:
                    usage_type = "serialization"
                elif f"self.{field_name} =" in line_content and "__init__" in content[:match.start()][-500:]:
                    usage_type = "initialization"
                elif f"rel.{field_name} =" in line_content or f"relationship.{field_name} =" in line_content:
                    usage_type = "write"
                elif f"self.{field_name}" in line_content and "return" in line_content:
                    usage_type = "read (return)"
                else:
                    usage_type = "read (logic)"

                usages.append({
                    "file": str(py_file),
                    "line": line_num,
                    "type": usage_type,
                    "content": line_content[:80]
                })
        except Exception as e:
            pass

    return usages

# Analyze all fields
print("=" * 80)
print("RELATIONSHIP FIELD USAGE ANALYSIS")
print("=" * 80)
print()

field_stats = {}
for field in ALL_FIELDS:
    usages = find_field_usage(field)

    # Categorize
    categories = defaultdict(int)
    for usage in usages:
        categories[usage["type"]] += 1

    # Determine if field is actually used
    real_usage = categories.get("read (logic)", 0) + categories.get("write", 0)

    field_stats[field] = {
        "total": len(usages),
        "real_usage": real_usage,
        "categories": dict(categories),
        "usages": usages
    }

# Categorize fields
used_fields = []
unused_fields = []

for field, stats in field_stats.items():
    if stats["real_usage"] > 0:
        used_fields.append(field)
    else:
        unused_fields.append(field)

# Print results
print(f"USED FIELDS ({len(used_fields)}):")
print("=" * 80)
for field in sorted(used_fields):
    stats = field_stats[field]
    print(f"  ✅ {field:40} - {stats['real_usage']} logical usages")
    if stats['real_usage'] <= 5:
        # Show details for lightly used fields
        for usage in stats['usages']:
            if usage['type'] in ['write', 'read (logic)']:
                print(f"      {usage['file']}:{usage['line']} ({usage['type']})")

print()
print(f"UNUSED FIELDS ({len(unused_fields)}):")
print("=" * 80)
for field in sorted(unused_fields):
    stats = field_stats[field]
    print(f"  ❌ {field:40} - only serialization/init")

print()
print("=" * 80)
print(f"SUMMARY: {len(used_fields)}/{len(ALL_FIELDS)} fields used")
print(f"         {len(unused_fields)}/{len(ALL_FIELDS)} fields unused (candidates for removal)")
print("=" * 80)
