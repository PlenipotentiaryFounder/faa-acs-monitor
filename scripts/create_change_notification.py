#!/usr/bin/env python3
"""
Create GitHub notifications for FAA ACS document changes
"""

import json
import os
from datetime import datetime
from pathlib import Path
from github import Github

def create_change_notification():
    """Create GitHub issue for detected changes"""
    
    # Load changes
    changes_file = Path("data/metadata/changes.json")
    if not changes_file.exists():
        print("No changes file found")
        return
    
    with open(changes_file, 'r') as f:
        changes = json.load(f)
    
    if not changes:
        print("No changes to report")
        return
    
    # Get GitHub token
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("GITHUB_TOKEN not found")
        return
    
    # Initialize GitHub client
    g = Github(token)
    repo = g.get_repo(os.environ.get('GITHUB_REPOSITORY', 'PlenipotentiaryFounder/faa-acs-monitor'))
    
    # Create issue content
    title = f"📄 FAA ACS Documents Updated - {datetime.now().strftime('%Y-%m-%d')}"
    
    body_lines = [
        "## FAA ACS Document Changes Detected",
        "",
        f"**Detection Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Changes:** {len(changes)}",
        ""
    ]
    
    for change in changes:
        doc = change['document']
        change_type = change['type'].title()
        
        body_lines.extend([
            f"### {change_type}: {doc['name']}",
            f"- **URL:** {doc['url']}",
            f"- **Last Modified:** {doc.get('last_modified', 'Unknown')}",
            f"- **File Size:** {doc.get('file_size', 'Unknown')} bytes",
            f"- **Content Hash:** `{doc.get('content_hash', 'Unknown')[:16]}...`",
            ""
        ])
    
    body_lines.extend([
        "## Next Steps",
        "- [ ] Review document changes",
        "- [ ] Update training materials if needed",
        "- [ ] Check compliance requirements",
        "- [ ] Notify relevant stakeholders",
        "",
        "---",
        "*This issue was automatically created by the FAA ACS monitoring system.*"
    ])
    
    body = "\n".join(body_lines)
    
    # Create the issue
    issue = repo.create_issue(
        title=title,
        body=body,
        labels=['faa-acs', 'document-update', 'automated']
    )
    
    print(f"Created issue: {issue.html_url}")

if __name__ == "__main__":
    create_change_notification()