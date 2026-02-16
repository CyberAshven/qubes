# DOCUMENT Blocks & File Access System - Architecture Plan

**Status:** Planning Phase (Not Yet Implemented)
**Created:** 2026-01-22
**Target Version:** Future Release

---

## Executive Summary

This document outlines the architecture for a comprehensive file access and document management system within Qubes. The system introduces a new DOCUMENT block type and file operation tools that enable Qubes to read, create, and modify files while maintaining full sovereignty, cryptographic verification, and audit trails.

**Key Features:**
- New DOCUMENT block type for permanent storage of created/modified files
- File operation tools (read_file, write_file, list_files, etc.)
- Sandboxed workspace with granular permission controls
- Git-like diff tracking for version history
- All data stored on-chain (no external dependencies)
- Complete audit trail of all file operations

---

## Table of Contents

1. [Use Cases & Vision](#use-cases--vision)
2. [Design Principles](#design-principles)
3. [DOCUMENT Block Architecture](#document-block-architecture)
4. [File Access Tools](#file-access-tools)
5. [Workspace Structure](#workspace-structure)
6. [Permission System](#permission-system)
7. [Security Model](#security-model)
8. [Version Control & Diffs](#version-control--diffs)
9. [User Interface](#user-interface)
10. [Implementation Phases](#implementation-phases)
11. [Technical Specifications](#technical-specifications)
12. [Trade-offs & Decisions](#trade-offs--decisions)

---

## Use Cases & Vision

### Primary Use Cases

1. **Coding Tasks**
   - User: "Build me a Python script to analyze this CSV data"
   - Qube reads data, writes Python script, creates tests
   - All code stored in DOCUMENT blocks with version history
   - User can see exactly what changed between iterations

2. **Document Creation**
   - User: "Write a research report on blockchain scalability"
   - Qube creates markdown document, makes revisions based on feedback
   - Every edit tracked with diffs showing what changed
   - Final document cryptographically signed by Qube

3. **Mixed Workflows**
   - User: "Help me refactor my website code"
   - Qube reads existing files (with permission)
   - Suggests changes, implements them
   - User reviews diffs before accepting
   - Modified files stored with full history

### Vision Statement

Enable Qubes to be **true development partners** while maintaining:
- **Sovereignty**: All files owned by user, stored in their chain
- **Transparency**: Every file operation logged and verifiable
- **Auditability**: Complete history of what was created/changed and why
- **Portability**: Entire workspace can be exported or sold with trained Qube

---

## Design Principles

### 1. On-Chain Storage Only
**Decision:** Store all file content directly in DOCUMENT blocks, not in external storage.

**Rationale:**
- Most files (code, documents) are small (5-50KB)
- Storage is cheap and getting cheaper
- True sovereignty requires no external dependencies
- Enables cryptographic verification of entire workspace
- Simplifies backup/transfer (entire chain = entire workspace)

**Comparison:**
- A Python file: ~10KB
- A markdown essay: ~5KB
- An entire small codebase: ~1MB across 50 files
- Modern storage easily handles this

### 2. Redundancy for Robustness
**Decision:** Store both full content AND diffs in DOCUMENT blocks.

**Rationale:**
- Full content: Easy retrieval, no reconstruction needed
- Diffs: Human-readable change history
- Storage cost is negligible vs. complexity savings
- Enables validation (apply diff to previous → should match current)

### 3. Explicit Over Implicit
**Decision:** File operations only via tools, not automatic scanning.

**Rationale:**
- Qube must consciously choose to create/modify files
- Prevents accidental file creation
- Clear audit trail (every operation in ACTION block)
- User has control

### 4. Workspace Isolation
**Decision:** Lock workspace files to Qube-only access, prevent manual user edits.

**Rationale:**
- Prevents version drift (disk ≠ chain)
- Maintains single source of truth
- User can still export and edit elsewhere
- Reduces complexity of merge conflicts

---

## DOCUMENT Block Architecture

### Block Structure

```json
{
  "block_type": "DOCUMENT",
  "block_number": 42,
  "timestamp": "2026-01-22T14:30:00Z",
  "previous_hash": "abc123...",
  "signature": "qube_ecdsa_signature...",

  "content": {
    // === Identity (Stable) ===
    "file_id": "ws_report_md_001",
    "filename": "report.md",
    "path": "outputs/reports/report.md",

    // === Operation Metadata ===
    "operation": "create|update|delete",
    "version": 3,
    "previous_version_block": 38,

    // === Content (Dual Storage) ===
    "content": "# Final Report\n\nThis is the current version...",
    "diff": "@@ -1,3 +1,4 @@\n-# Report\n+# Final Report\n...",

    // === Validation ===
    "size_bytes": 1024,
    "content_type": "text/markdown",
    "encoding": "utf-8",
    "hash": "sha256_current_content",
    "previous_hash": "sha256_previous_content",

    // === Attribution ===
    "created_by": "write_file_tool",
    "edit_reason": "Expanded analysis section per user request",
    "related_message_block": 40
  }
}
```

### Block Types by Operation

**CREATE (Initial Version):**
```json
{
  "operation": "create",
  "version": 1,
  "previous_version_block": null,
  "content": "full initial content",
  "diff": null,
  "previous_hash": null
}
```

**UPDATE (Subsequent Versions):**
```json
{
  "operation": "update",
  "version": 2,
  "previous_version_block": 35,
  "content": "full updated content",
  "diff": "unified diff from v1 to v2",
  "previous_hash": "hash_of_v1"
}
```

**DELETE (Soft Delete):**
```json
{
  "operation": "delete",
  "version": 4,
  "previous_version_block": 38,
  "content": null,
  "diff": null,
  "deletion_reason": "File no longer needed"
}
```

### File ID Generation

```python
def generate_file_id(path: str) -> str:
    """
    Generate stable ID for file across versions.

    Examples:
    - "outputs/report.md" → "ws_report_md_001"
    - "code/script.py" → "ws_script_py_002"
    """
    # Sanitize filename
    filename = path.split('/')[-1]
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')

    # Create base ID
    base = f"ws_{name}_{ext}".replace('-', '_').replace(' ', '_')

    # Append counter to ensure uniqueness
    counter = 1
    while workspace_index.has_file_id(f"{base}_{counter:03d}"):
        counter += 1

    return f"{base}_{counter:03d}"
```

---

## File Access Tools

### read_file

**Tool Definition:**
```json
{
  "name": "read_file",
  "description": "Read contents of a file from workspace or permitted directory. Returns file content as string for text files.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File path. Use relative path for workspace/ or absolute path for permitted external directories."
      }
    },
    "required": ["path"]
  }
}
```

**Implementation:**
```python
async def read_file(path: str) -> str:
    """
    Read file with security validation.

    Returns: File content as string
    Raises: PermissionError, FileNotFoundError
    """
    # Security check
    validate_file_access(qube, path, operation="read")

    # Normalize path
    normalized = resolve_path(qube, path)

    # Read file
    with open(normalized, 'r', encoding='utf-8') as f:
        content = f.read()

    # Log in ACTION block
    create_action_block(
        action_type="read_file",
        parameters={"path": path},
        result={"size_bytes": len(content), "success": True}
    )

    return content
```

### write_file

**Tool Definition:**
```json
{
  "name": "write_file",
  "description": "Create or update a file. Automatically creates DOCUMENT block with version history and diff tracking.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File path in workspace/ or permitted directory"
      },
      "content": {
        "type": "string",
        "description": "Full file content to write"
      },
      "reason": {
        "type": "string",
        "description": "Optional explanation of why this change was made"
      }
    },
    "required": ["path", "content"]
  }
}
```

**Implementation:**
```python
async def write_file(path: str, content: str, reason: str = None) -> dict:
    """
    Write file and create DOCUMENT block.

    Returns: {
        "file_id": "ws_report_md_001",
        "operation": "create|update",
        "version": 2,
        "block_number": 42
    }
    """
    # Security check
    validate_file_access(qube, path, operation="write")

    # Resolve path
    normalized = resolve_path(qube, path)

    # Check if file exists (create vs update)
    file_id = workspace_index.get_file_id(normalized)
    is_update = file_id is not None

    if is_update:
        # Get previous version for diff
        prev_block = get_latest_document_block(file_id)
        prev_content = prev_block.content.content

        # Compute diff
        diff = compute_unified_diff(prev_content, content)

        operation = "update"
        version = prev_block.content.version + 1
        previous_version_block = prev_block.block_number
        previous_hash = prev_block.content.hash
    else:
        # New file
        file_id = generate_file_id(path)
        diff = None
        operation = "create"
        version = 1
        previous_version_block = None
        previous_hash = None

    # Write to disk
    with open(normalized, 'w', encoding='utf-8') as f:
        f.write(content)

    # Create DOCUMENT block
    doc_block = create_document_block(
        file_id=file_id,
        filename=os.path.basename(path),
        path=path,
        operation=operation,
        version=version,
        previous_version_block=previous_version_block,
        content=content,
        diff=diff,
        previous_hash=previous_hash,
        edit_reason=reason
    )

    # Update workspace index
    workspace_index.update(file_id, doc_block.block_number)

    # Log in ACTION block
    create_action_block(
        action_type="write_file",
        parameters={"path": path},
        result={
            "file_id": file_id,
            "operation": operation,
            "version": version,
            "block_number": doc_block.block_number
        }
    )

    return {
        "file_id": file_id,
        "operation": operation,
        "version": version,
        "block_number": doc_block.block_number
    }
```

### list_files

**Tool Definition:**
```json
{
  "name": "list_files",
  "description": "List files in a directory. Returns array of file paths.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Directory path to list"
      },
      "pattern": {
        "type": "string",
        "description": "Optional glob pattern to filter files (e.g., '*.py', '*.md')"
      },
      "recursive": {
        "type": "boolean",
        "description": "Whether to list files recursively"
      }
    },
    "required": ["path"]
  }
}
```

### search_in_files

**Tool Definition:**
```json
{
  "name": "search_in_files",
  "description": "Search for text pattern across multiple files (like grep). Returns matches with context.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Directory to search in"
      },
      "pattern": {
        "type": "string",
        "description": "Text pattern to search for (supports regex)"
      },
      "file_pattern": {
        "type": "string",
        "description": "Optional glob to filter which files to search (e.g., '*.py')"
      }
    },
    "required": ["path", "pattern"]
  }
}
```

### get_file_history

**Tool Definition:**
```json
{
  "name": "get_file_history",
  "description": "Get version history of a file with all changes and diffs.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "File path to get history for"
      }
    },
    "required": ["path"]
  }
}
```

**Returns:**
```json
{
  "file_id": "ws_report_md_001",
  "current_version": 3,
  "versions": [
    {
      "version": 3,
      "block_number": 42,
      "timestamp": "2026-01-22T14:30:00Z",
      "operation": "update",
      "edit_reason": "Expanded analysis",
      "size_bytes": 1024,
      "diff": "@@ -1,3 +1,4 @@..."
    },
    {
      "version": 2,
      "block_number": 38,
      "timestamp": "2026-01-21T10:15:00Z",
      "operation": "update",
      "edit_reason": "Added analysis section",
      "size_bytes": 856
    },
    {
      "version": 1,
      "block_number": 35,
      "timestamp": "2026-01-20T16:00:00Z",
      "operation": "create",
      "size_bytes": 512
    }
  ]
}
```

---

## Workspace Structure

### Directory Layout

```
data/users/{user_id}/qubes/{qube_id}/
├── workspace/              # Qube's file workspace (locked to Qube-only access)
│   ├── inputs/            # User-provided input files
│   ├── outputs/           # Qube-created documents/files
│   ├── code/              # Code files
│   └── temp/              # Temporary/scratch files
├── blocks/
│   └── permanent/         # DOCUMENT blocks stored here
├── chain/
│   └── chain_state.json   # Includes workspace_index
└── ...
```

### Workspace Index (in chain_state)

```json
"workspace_index": {
  "ws_report_md_001": {
    "path": "outputs/reports/report.md",
    "current_block": 42,
    "current_version": 3,
    "current_hash": "sha256...",
    "created_block": 35,
    "modified_block": 42,
    "size_bytes": 1024,
    "content_type": "text/markdown",
    "is_deleted": false
  },
  "ws_script_py_001": {
    "path": "code/data_analyzer.py",
    "current_block": 45,
    "current_version": 1,
    "current_hash": "sha256...",
    "created_block": 45,
    "modified_block": 45,
    "size_bytes": 2048,
    "content_type": "text/x-python",
    "is_deleted": false
  }
}
```

---

## Permission System

### Storage in chain_state

```json
"file_permissions": {
  "/projects/website": {
    "read": true,
    "write": true,
    "granted_at": "2026-01-22T12:00:00Z",
    "granted_by": "user",
    "file_type_filter": "all"  // "text_only", "text_and_pdf", "all"
  },
  "/documents/essays": {
    "read": true,
    "write": false,
    "granted_at": "2026-01-22T12:00:00Z",
    "granted_by": "user",
    "file_type_filter": "text_only"
  }
},
"file_safety_settings": {
  "block_system_directories": true,
  "block_sensitive_files": true,
  "require_delete_confirmation": true,
  "log_all_operations": false,
  "allowed_file_types": "all"  // "text_only", "text_and_pdf", "all"
}
```

### Permission Levels

**Workspace (Always Enabled):**
- Full read/write access to `workspace/` directory
- No user approval needed
- All operations logged in ACTION blocks

**External Directories (Opt-In):**
- User explicitly grants access via Settings tab
- Can grant read-only or read-write
- Can restrict to specific file types
- Can revoke at any time

### Settings UI

```
┌─────────────────────────────────────────────────────────┐
│ File Access Permissions                                  │
│                                                           │
│ Workspace Access (Always Enabled):                       │
│ ✓ Full read/write access to workspace/                  │
│                                                           │
│ External Directory Access:                               │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Path                    Read    Write    Remove   │   │
│ ├───────────────────────────────────────────────────┤   │
│ │ /projects/website/      [✓]     [✓]      [×]     │   │
│ │ /documents/essays/      [✓]     [ ]      [×]     │   │
│ │ /work/reports/          [✓]     [✓]      [×]     │   │
│ └───────────────────────────────────────────────────┘   │
│                                                           │
│ [+ Add Directory Permission]                             │
│                                                           │
│ File Type Restrictions:                                  │
│ ○ Text files only (.txt, .py, .md, .json, etc.)         │
│ ○ Text + PDFs                                            │
│ ● All supported file types                               │
│                                                           │
│ Safety Settings:                                         │
│ [✓] Block system directories (/etc, /usr, /sys)         │
│ [✓] Block sensitive files (.env, credentials, keys)     │
│ [✓] Require confirmation for file deletion              │
│ [ ] Log all file operations to console                  │
│                                                           │
│ DOCUMENT Block Settings:                                 │
│ Auto-approve DOCUMENT blocks:                            │
│ ○ Always require manual approval                        │
│ ● Auto-approve (trust mode)                             │
│ ○ Auto-approve for workspace/ only                      │
└─────────────────────────────────────────────────────────┘
```

---

## Security Model

### Multi-Layer Security

```python
def validate_file_access(qube, path: str, operation: str) -> bool:
    """
    Multi-layer security validation.

    Raises appropriate error if access denied.
    Returns True if allowed.
    """
    # Layer 1: Normalize path (resolve .., symlinks, etc.)
    normalized = os.path.realpath(path)

    # Layer 2: Check if in workspace (always allowed)
    if normalized.startswith(qube.workspace_path):
        return True

    # Layer 3: Blacklist validation
    if is_blacklisted(normalized):
        raise SecurityError(
            f"Cannot access system/sensitive path: {path}",
            blacklist_reason=get_blacklist_reason(normalized)
        )

    # Layer 4: Check explicit permissions
    perms = qube.chain_state.get("file_permissions", {})

    for granted_path, access in perms.items():
        if normalized.startswith(granted_path):
            # Check read permission
            if operation == "read" and access["read"]:
                return validate_file_type(normalized, access["file_type_filter"])

            # Check write permission
            if operation == "write" and access["write"]:
                return validate_file_type(normalized, access["file_type_filter"])

    # Layer 5: No permission found
    raise PermissionError(
        f"No {operation} permission for {path}. "
        f"Grant access in Settings → File Permissions"
    )
```

### Blacklist Implementation

```python
# System directories (cannot access)
BLACKLISTED_PATHS = {
    "/etc", "/usr", "/sys", "/proc", "/dev", "/boot",
    "/Windows", "/System32", "/System", "/Library",
    "C:\\Windows", "C:\\Program Files"
}

# Sensitive file patterns (cannot access)
BLACKLISTED_PATTERNS = {
    ".env", ".env.*",
    "credentials", "credential",
    "secret", "secrets",
    "private_key", "private-key",
    ".ssh", "id_rsa", "id_dsa", "id_ecdsa",
    "password", "passwd",
    "*.key", "*.pem",
    "wallet.dat"
}

def is_blacklisted(path: str) -> bool:
    """Check if path is blacklisted."""
    # Check exact path matches
    for blocked_path in BLACKLISTED_PATHS:
        if path.startswith(blocked_path):
            return True

    # Check filename patterns
    filename = os.path.basename(path)
    for pattern in BLACKLISTED_PATTERNS:
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            return True

    return False
```

### File Type Validation

```python
def validate_file_type(path: str, filter: str) -> bool:
    """
    Validate file type against permission filter.

    filter: "text_only", "text_and_pdf", "all"
    """
    extension = path.split('.')[-1].lower()

    TEXT_EXTENSIONS = {
        'txt', 'md', 'py', 'js', 'ts', 'html', 'css', 'json',
        'yaml', 'yml', 'xml', 'csv', 'sql', 'sh', 'rs', 'go',
        'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'rb', 'php'
    }

    if filter == "text_only":
        if extension not in TEXT_EXTENSIONS:
            raise SecurityError(f"Only text files allowed. Cannot access .{extension} file")
        return True

    elif filter == "text_and_pdf":
        if extension not in TEXT_EXTENSIONS and extension != 'pdf':
            raise SecurityError(f"Only text and PDF files allowed. Cannot access .{extension} file")
        return True

    elif filter == "all":
        return True

    return False
```

---

## Version Control & Diffs

### Diff Computation

```python
import difflib

def compute_unified_diff(old_content: str, new_content: str) -> str:
    """
    Compute unified diff between two versions.

    Returns diff in standard unified format (like git diff).
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="old version",
        tofile="new version",
        lineterm=''
    )

    return ''.join(diff)
```

**Example Output:**
```diff
@@ -1,4 +1,4 @@
 # Report

-This is version 2.
+This is version 3.
+
+Added new analysis section.
```

### Diff Application (Validation)

```python
def apply_unified_diff(old_content: str, diff: str) -> str:
    """
    Apply unified diff to reconstruct new content.

    Used for validation: should match stored content.
    """
    import patch

    # Apply patch
    new_content = patch.fromstring(old_content, diff)

    return new_content

def validate_document_block_integrity(current_block):
    """
    Validate that diff + previous = current.

    Ensures chain integrity for DOCUMENT blocks.
    """
    if current_block.content.operation == "create":
        # No previous version to validate against
        return True

    # Get previous version
    prev_block_num = current_block.content.previous_version_block
    prev_block = chain.get_block(prev_block_num)

    # Apply diff to previous content
    reconstructed = apply_unified_diff(
        prev_block.content.content,
        current_block.content.diff
    )

    # Should match current content
    if reconstructed != current_block.content.content:
        raise IntegrityError(
            f"DOCUMENT block {current_block.block_number} failed validation. "
            f"Diff does not reconstruct current content."
        )

    # Verify hash
    computed_hash = hashlib.sha256(
        current_block.content.content.encode()
    ).hexdigest()

    if computed_hash != current_block.content.hash:
        raise IntegrityError(
            f"DOCUMENT block {current_block.block_number} hash mismatch"
        )

    return True
```

### Time Travel Queries

```python
def get_file_content_at_version(file_id: str, version: int) -> str:
    """Get file content at specific version (easy - full content stored)."""
    block = chain.get_document_block_by_version(file_id, version)
    return block.content.content

def get_file_content_at_time(file_id: str, timestamp: datetime) -> str:
    """Get file content as it was at specific time."""
    block = chain.get_document_block_before_time(file_id, timestamp)
    return block.content.content if block else None

def get_file_changes_between_versions(file_id: str, from_version: int, to_version: int) -> list:
    """Get all changes between two versions."""
    blocks = chain.get_document_blocks_range(file_id, from_version, to_version)

    changes = []
    for block in blocks:
        changes.append({
            "version": block.content.version,
            "timestamp": block.timestamp,
            "diff": block.content.diff,
            "reason": block.content.edit_reason
        })

    return changes
```

---

## User Interface

### New "Workspace" Tab

```
┌─────────────────────────────────────────────────────────┐
│ [Folder Tree]        │ [File Viewer]                    │
│                      │                                   │
│ 📁 inputs/           │ 📄 report.md (v3, modified 2h ago)│
│   📄 data.csv        │                                   │
│ 📁 outputs/          │ # Final Report                    │
│   📁 reports/        │                                   │
│     📄 report.md ●   │ This is the current version...    │
│   📁 images/         │                                   │
│ 📁 code/             │                                   │
│   📄 analyzer.py     │                                   │
│   📄 tests.py        │                                   │
│ 📁 temp/             │                                   │
│                      │                                   │
│ [+ New File]         │ [View History] [Export] [Delete]  │
│ [Import Files]       │                                   │
└─────────────────────────────────────────────────────────┘
```

### File History View

**Click "View History" button:**

```
┌─────────────────────────────────────────────────────────┐
│ File History: outputs/reports/report.md                 │
│                                                           │
│ ● Version 3 (current) - 2 hours ago - Block #42         │
│   Changed by: write_file tool                           │
│   Reason: "Expanded analysis section per user request"  │
│   Size: 1,024 bytes                                     │
│   Hash: a7b3c9d...                                      │
│   [View Content] [View Diff] [Restore This Version]     │
│                                                           │
│ ○ Version 2 - 1 day ago - Block #38                     │
│   Changed by: write_file tool                           │
│   Reason: "Added analysis section"                      │
│   Size: 856 bytes                                       │
│   Hash: d4e5f6a...                                      │
│   [View Content] [View Diff] [Restore This Version]     │
│                                                           │
│ ○ Version 1 (initial) - 2 days ago - Block #35          │
│   Created by: write_file tool                           │
│   Reason: "Initial report creation"                     │
│   Size: 512 bytes                                       │
│   Hash: abc1234...                                      │
│   [View Content]                                        │
└─────────────────────────────────────────────────────────┘
```

### Diff Viewer

**Click "View Diff" on Version 3:**

```
┌─────────────────────────────────────────────────────────┐
│ Changes in Version 3 (Block #42)                         │
│ From Version 2 → Version 3                               │
│                                                           │
│ @@ -1,4 +1,6 @@                                          │
│   # Report                                               │
│                                                           │
│ - This is version 2.                                     │
│ + This is version 3.                                     │
│ +                                                        │
│ + ## Analysis                                            │
│ + Detailed analysis of the findings...                   │
│                                                           │
│ [Previous Diff] [Next Diff] [Close]                      │
└─────────────────────────────────────────────────────────┘
```

### File Content Viewer

**Syntax Highlighting by File Type:**
- Python: Full syntax highlighting
- Markdown: Rendered preview option
- JSON: Formatted with collapsible sections
- CSV: Table view option
- Images: Preview (if stored)

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
**Goal:** Basic file operations and DOCUMENT blocks working

**Tasks:**
- [ ] Define DOCUMENT block type in core/block.py
- [ ] Create workspace/ directory structure on qube creation
- [ ] Implement `read_file` tool
- [ ] Implement `write_file` tool
- [ ] Implement `list_files` tool
- [ ] Add workspace_index to chain_state
- [ ] Basic permission validation (workspace-only)
- [ ] ACTION block logging for all file operations

**Deliverable:** Can read/write files in workspace, creates DOCUMENT blocks

---

### Phase 2: Diff Engine (Week 1-2)
**Goal:** Version tracking with diffs

**Tasks:**
- [ ] Integrate difflib for unified diff computation
- [ ] Modify write_file to compute diffs on update
- [ ] Store diff in DOCUMENT blocks
- [ ] Implement diff validation (apply to previous → match current)
- [ ] Add version tracking to workspace_index
- [ ] Implement file_id generation
- [ ] Link versions via previous_version_block

**Deliverable:** Full version history with diffs, validation working

---

### Phase 3: UI - Workspace Tab (Week 2)
**Goal:** Visual interface for file management

**Tasks:**
- [ ] Create new Workspace tab in qubes-gui
- [ ] Implement file tree browser component
- [ ] Implement file content viewer with syntax highlighting
- [ ] Create history timeline view
- [ ] Implement diff viewer component
- [ ] Add export file functionality
- [ ] Add file metadata display (size, type, hash)

**Deliverable:** Complete UI for browsing workspace and viewing history

---

### Phase 4: Permissions UI (Week 2-3)
**Goal:** User control over external directory access

**Tasks:**
- [ ] Add File Permissions section to Settings tab
- [ ] Implement directory picker for granting access
- [ ] Add permission table (path, read, write toggles)
- [ ] Implement permission revocation
- [ ] Add file type filter UI
- [ ] Add safety settings toggles
- [ ] Store permissions in chain_state
- [ ] Implement blacklist validation

**Deliverable:** Users can grant/revoke directory access via UI

---

### Phase 5: Advanced Features (Week 3-4)
**Goal:** Polish and advanced capabilities

**Tasks:**
- [ ] Implement `search_in_files` tool (grep-like)
- [ ] Implement `get_file_history` tool
- [ ] Add "Restore to previous version" functionality
- [ ] Implement merge conflict detection
- [ ] Add conflict resolution UI
- [ ] Create DOCUMENT block gallery view
- [ ] Add bulk export (zip workspace)

**Deliverable:** Full-featured file management system

---

### Phase 6: Binary Files & Polish (Week 4+)
**Goal:** Support non-text files and final polish

**Tasks:**
- [ ] Add PDF support (text extraction for input, base64 for output)
- [ ] Add image support (DALL-E integration → DOCUMENT block)
- [ ] Implement markdown preview mode
- [ ] Add code syntax highlighting improvements
- [ ] Performance optimization for large files
- [ ] Add file size warnings (>100KB)
- [ ] Comprehensive testing
- [ ] Documentation updates

**Deliverable:** Production-ready system

---

## Technical Specifications

### Supported File Types

**Phase 1 (Text Only):**
```python
TEXT_EXTENSIONS = {
    # Programming Languages
    'py', 'js', 'ts', 'jsx', 'tsx', 'rs', 'go', 'java', 'c', 'cpp',
    'h', 'hpp', 'cs', 'rb', 'php', 'swift', 'kt', 'scala', 'r',

    # Web
    'html', 'css', 'scss', 'sass', 'less', 'vue', 'svelte',

    # Config & Data
    'json', 'yaml', 'yml', 'toml', 'xml', 'ini', 'cfg', 'conf',
    'csv', 'tsv', 'sql',

    # Documentation
    'md', 'markdown', 'txt', 'rst', 'tex',

    # Scripts
    'sh', 'bash', 'zsh', 'ps1', 'bat', 'cmd'
}
```

**Phase 2 (Binary):**
- PDF (text extraction + base64 storage)
- Images (png, jpg, webp - base64 storage)
- DOCX (text extraction)

### File Size Limits

**Recommended:**
- Text files: No hard limit (warn at 100KB)
- Binary files: Warn at 1MB, hard limit at 5MB

**Rationale:**
- Most code files: 5-50KB
- Documentation: 10-100KB
- 100KB = ~3,000 lines of code
- Storage is cheap, but UX suffers with huge files in UI

### Character Encoding

**Default:** UTF-8 for all text files

**Handling:**
```python
# Always specify encoding
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# For binary (PDFs, images)
with open(path, 'rb') as f:
    binary_data = f.read()
    base64_data = base64.b64encode(binary_data).decode('ascii')
```

### Hash Algorithm

**Standard:** SHA-256 for all file content hashes

```python
import hashlib

def compute_file_hash(content: str) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### Content Type Detection

```python
import mimetypes

def detect_content_type(path: str) -> str:
    """Detect MIME type from file extension."""
    content_type, _ = mimetypes.guess_type(path)

    if content_type is None:
        # Fallback based on extension
        ext = path.split('.')[-1].lower()
        fallback_types = {
            'md': 'text/markdown',
            'py': 'text/x-python',
            'js': 'application/javascript',
            'json': 'application/json',
            'yaml': 'application/x-yaml'
        }
        content_type = fallback_types.get(ext, 'text/plain')

    return content_type
```

---

## Trade-offs & Decisions

### 1. File Operations via Tools (Not Auto-Sync)

**Decision:** File operations only via AI tools (read_file, write_file), not automatic workspace scanning.

**Trade-off:**
- ✅ Explicit audit trail (every operation in ACTION block)
- ✅ Qube must consciously choose to create files
- ✅ User has control and visibility
- ❌ Qube can't "discover" user-added files automatically
- ❌ User must prompt Qube to read files

**Rationale:** Explicit is better than implicit for security and auditability.

---

### 2. Lock Workspace Files (Qube-Only Access)

**Decision:** Workspace files are locked - only Qube can modify them via tools.

**Trade-off:**
- ✅ Single source of truth (disk = chain)
- ✅ No version drift or merge conflicts
- ✅ Simpler implementation
- ❌ User can't manually edit files in workspace
- ❌ Must export to edit elsewhere

**Rationale:** Prevents complexity of reconciling manual edits with chain state.

**User Workaround:** Export file → Edit elsewhere → Ask Qube to incorporate changes

---

### 3. Soft Delete (Not Hard Delete)

**Decision:** Deleting a file creates DOCUMENT block with operation="delete" and content=null.

**Trade-off:**
- ✅ Complete audit trail ("Alph deleted config.py at 3pm")
- ✅ Can see what was deleted and why
- ✅ Can potentially restore if needed
- ❌ Slightly more complex queries (filter out deleted files)
- ❌ Storage used for deleted file marker

**Rationale:** Audit trail is more valuable than storage savings.

**Implementation:**
```python
# Workspace index marks as deleted
"ws_config_py_001": {
    "is_deleted": true,
    "deleted_block": 50,
    "deleted_reason": "No longer needed"
}

# Queries automatically filter
def list_active_files():
    return [
        f for f in workspace_index.values()
        if not f.get("is_deleted", False)
    ]
```

---

### 4. Store Diff + Full Content (Redundant but Robust)

**Decision:** DOCUMENT blocks store BOTH the full current content AND the diff from previous version.

**Trade-off:**
- ✅ Easy retrieval (no reconstruction needed)
- ✅ Can validate (apply diff → should match content)
- ✅ Human-readable change history via diffs
- ✅ Simpler queries
- ❌ ~2x storage per update (diff + content)

**Rationale:** Storage is cheap, complexity is expensive. Redundancy provides safety and simplicity.

**Storage Analysis:**
```
Example: 10KB file with 5 versions
- Full content each time: 50KB total
- With diffs: ~15KB diffs + 50KB content = 65KB total
- Overhead: 30% for huge UX/reliability benefit
```

---

### 5. Auto-Approve vs Manual Review (User Choice)

**Decision:** Add setting for DOCUMENT block approval mode.

**Options:**
1. **Always require approval:** User reviews every file creation/edit
2. **Auto-approve (trust mode):** Files created automatically without confirmation
3. **Auto-approve workspace only:** External directories still require approval

**Implementation:**
```python
# In chain_state
"document_approval_mode": "auto_approve"  # or "manual_review", "workspace_only"

# Before creating DOCUMENT block
if should_require_approval(operation, path):
    # Show confirmation dialog in UI
    approved = await request_user_approval(file_preview)
    if not approved:
        raise UserDeniedError("User did not approve file creation")

# Create DOCUMENT block
create_document_block(...)
```

---

### 6. Merge Conflicts (User Chooses Resolution)

**Decision:** If manual edit detected, show conflict UI with three options.

**Scenario:** User exports file, edits manually, Qube tries to update same file.

**Detection:**
```python
def detect_manual_edit(file_id: str) -> bool:
    """Detect if file on disk differs from latest DOCUMENT block."""
    latest_block = get_latest_document_block(file_id)
    disk_content = read_file_from_disk(latest_block.content.path)

    disk_hash = compute_file_hash(disk_content)
    chain_hash = latest_block.content.hash

    return disk_hash != chain_hash
```

**Conflict Resolution UI:**
```
┌─────────────────────────────────────────────────────────┐
│ ⚠️  Merge Conflict Detected                             │
│                                                           │
│ File: outputs/report.md                                  │
│                                                           │
│ The file has been modified both:                         │
│ - On disk (manual edit)                                  │
│ - By Qube (new version)                                  │
│                                                           │
│ [Keep My Changes]  [Keep Qube's Changes]  [Merge Both]  │
│                                                           │
│ Preview:                                                 │
│ ┌─────────────────────┬───────────────────────┐         │
│ │ Your Version        │ Qube's Version        │         │
│ ├─────────────────────┼───────────────────────┤         │
│ │ # My Report         │ # Final Report        │         │
│ │ Manual edit...      │ Qube's changes...     │         │
│ └─────────────────────┴───────────────────────┘         │
└─────────────────────────────────────────────────────────┘
```

---

## Example End-to-End Workflow

### Scenario: Building a Website

**User:** "Alph, I'm building a portfolio website. Help me create the HTML, CSS, and a Python backend."

**Alph's Response:** "I'll help you build a portfolio website. Let me create the initial structure."

**Internal Actions (Logged in ACTION blocks):**

1. `write_file("workspace/code/index.html", "<html>...")`
   → Creates DOCUMENT block #35 (v1, create)

2. `write_file("workspace/code/about.html", "<html>...")`
   → Creates DOCUMENT block #36 (v1, create)

3. `write_file("workspace/code/style.css", "body { ... }")`
   → Creates DOCUMENT block #37 (v1, create)

4. `write_file("workspace/code/app.py", "from flask import ...")`
   → Creates DOCUMENT block #38 (v1, create)

**User sees in Workspace tab:**
```
📁 code/
  📄 index.html (v1, just now)
  📄 about.html (v1, just now)
  📄 style.css (v1, just now)
  📄 app.py (v1, just now)
```

---

**User:** "The header should be blue, not green. And add a contact page."

**Alph's Internal Actions:**

1. `read_file("workspace/code/style.css")` → Gets current CSS
   → Logged in ACTION block

2. `write_file("workspace/code/style.css", updated_css)`
   → Creates DOCUMENT block #39 with:
   - operation: update
   - version: 2
   - diff: Shows color change green → blue
   - full updated content

3. `write_file("workspace/code/contact.html", "<html>...")`
   → Creates DOCUMENT block #40 (v1, create)

**User clicks "View History" on style.css:**
```
● Version 2 (current) - just now - Block #39
  Reason: "Changed header color from green to blue"
  [View Diff]

  Diff shows:
  @@ -5,1 +5,1 @@
  - color: green;
  + color: blue;

○ Version 1 (initial) - 5 minutes ago - Block #37
  Reason: "Initial stylesheet creation"
  [View Content]
```

---

**User:** "Actually, I want the header to match my brand color #FF5733. Also, make the font size bigger."

**Alph's Internal Actions:**

1. `read_file("workspace/code/style.css")` → Gets v2

2. `write_file("workspace/code/style.css", v3_content)`
   → Creates DOCUMENT block #42 with:
   - version: 3
   - diff: Shows both color and font-size changes
   - previous_version_block: 39

**History now shows 3 versions:**
```
● v3 (current): Custom brand color + bigger font
○ v2: Blue header
○ v1 (initial): Green header
```

**User can:**
- View any version's content
- See exact diffs between any two versions
- Restore to previous version if needed
- Export any version to disk
- See complete audit trail of all changes

---

## Validation & Integrity

### Block Validation

Every DOCUMENT block must pass:

```python
def validate_document_block(block):
    """
    Comprehensive validation for DOCUMENT blocks.
    """
    # 1. Schema validation
    assert block.block_type == "DOCUMENT"
    assert block.content.file_id.startswith("ws_")
    assert block.content.operation in ["create", "update", "delete"]

    # 2. Version continuity
    if block.content.operation == "update":
        prev_block = chain.get_block(block.content.previous_version_block)
        assert prev_block.content.version == block.content.version - 1
        assert prev_block.content.file_id == block.content.file_id

    # 3. Hash validation
    computed_hash = hashlib.sha256(
        block.content.content.encode()
    ).hexdigest()
    assert computed_hash == block.content.hash

    # 4. Diff validation (for updates)
    if block.content.operation == "update" and block.content.diff:
        prev_block = chain.get_block(block.content.previous_version_block)
        reconstructed = apply_unified_diff(
            prev_block.content.content,
            block.content.diff
        )
        assert reconstructed == block.content.content

        # Verify previous_hash matches
        assert prev_block.content.hash == block.content.previous_hash

    # 5. Signature validation
    assert verify_block_signature(block)

    return True
```

### Chain Integrity Check

```python
def verify_document_chain_integrity(file_id: str):
    """
    Verify entire version history for a file.
    """
    blocks = chain.get_all_document_blocks(file_id)

    for i, block in enumerate(blocks):
        # Validate block itself
        validate_document_block(block)

        # Verify version sequence
        assert block.content.version == i + 1

        # Verify links
        if i > 0:
            assert block.content.previous_version_block == blocks[i-1].block_number

    return True
```

---

## Future Enhancements

### Post-v1 Features

1. **Collaborative Editing**
   - Multiple Qubes working on same file
   - Three-way merge (user, qube1, qube2)
   - Conflict resolution protocols

2. **External Tool Integration**
   - Git integration (push workspace to GitHub)
   - IDE plugins (VSCode, PyCharm)
   - CI/CD pipelines reading from workspace

3. **Advanced Search**
   - Full-text search across all versions
   - Semantic search using embeddings
   - "When did this function get added?"

4. **Workspace Snapshots**
   - Checkpoint entire workspace state
   - Tag important milestones
   - Restore workspace to previous state

5. **Binary Diff Support**
   - For images, track visual changes
   - For PDFs, track text content changes
   - Efficient storage of binary diffs

6. **Blockchain Anchoring**
   - Anchor workspace state to BCH
   - Prove file existed at specific time
   - NFT for code repositories

---

## Conclusion

This architecture provides a robust foundation for file access and document management within Qubes while maintaining core principles:

- **Sovereignty**: User owns all files, stored in their chain
- **Security**: Multi-layer validation with granular permissions
- **Transparency**: Every operation logged and auditable
- **Integrity**: Cryptographic verification of all content
- **Usability**: Git-like version control with friendly UI

The system is designed to grow incrementally, starting with basic file operations and expanding to advanced features as needed.

---

**Next Steps:**
1. Review and refine this plan
2. Prototype core DOCUMENT block structure
3. Implement Phase 1 (basic file operations)
4. Gather user feedback
5. Iterate and improve

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Authors:** bit_faced, Claude Sonnet 4.5
