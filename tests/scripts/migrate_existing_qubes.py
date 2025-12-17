"""
Migrate Existing Qubes to New Directory Structure

Fixes duplicate nesting: moves qubes from:
  data/users/{user}/qubes/{name_id}/qubes/{name_id}/
to:
  data/users/{user}/qubes/{name_id}/

Creates backup before migration.
"""

import shutil
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

console = Console()


def migrate_user_qubes(user_id: str, dry_run: bool = False):
    """Migrate all qubes for a user"""

    user_dir = Path("data") / "users" / user_id
    qubes_dir = user_dir / "qubes"

    if not qubes_dir.exists():
        console.print(f"[yellow]No qubes directory for user: {user_id}[/yellow]")
        return

    console.print(f"\n[bold cyan]Migrating qubes for user: {user_id}[/bold cyan]")

    migrated_count = 0

    for qube_dir in qubes_dir.iterdir():
        if not qube_dir.is_dir():
            continue

        # Check for duplicate nesting
        nested_qubes_dir = qube_dir / "qubes"
        if nested_qubes_dir.exists() and nested_qubes_dir.is_dir():
            nested_qube_dir = nested_qubes_dir / qube_dir.name

            if nested_qube_dir.exists():
                console.print(f"\n[yellow]Found duplicate nesting in: {qube_dir.name}[/yellow]")
                console.print(f"  From: {nested_qube_dir}")
                console.print(f"  To: {qube_dir}")

                if dry_run:
                    console.print("  [cyan](DRY RUN - would migrate)[/cyan]")
                    migrated_count += 1
                    continue

                # Create backup
                backup_dir = user_dir / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)

                backup_path = backup_dir / f"{qube_dir.name}_pre_migration_backup.tar.gz"

                console.print(f"  [cyan]Creating backup: {backup_path}[/cyan]")
                import tarfile
                with tarfile.open(backup_path, "w:gz") as tar:
                    tar.add(qube_dir, arcname=qube_dir.name)

                # Move files from nested dir to correct location
                console.print(f"  [green]Migrating files...[/green]")

                # Move each item from nested dir to parent
                for item in nested_qube_dir.iterdir():
                    target = qube_dir / item.name

                    # Skip if already exists at target (shouldn't happen)
                    if target.exists() and target != item:
                        console.print(f"    [yellow]Skipping {item.name} (already exists)[/yellow]")
                        continue

                    # Move the item
                    shutil.move(str(item), str(target))
                    console.print(f"    ✓ Moved: {item.name}")

                # Remove now-empty nested directories
                nested_qube_dir.rmdir()
                nested_qubes_dir.rmdir()

                console.print(f"  [green]✓ Migration complete for {qube_dir.name}[/green]")
                migrated_count += 1

    if migrated_count > 0:
        console.print(f"\n[bold green]✓ Migrated {migrated_count} qube(s) for user {user_id}[/bold green]")
    else:
        console.print(f"\n[bold green]✓ No migration needed for user {user_id}[/bold green]")


def main():
    """Main migration entry point"""

    console.print("\n[bold cyan]Qubes Directory Structure Migration[/bold cyan]")
    console.print("This will fix duplicate nesting in qube directories.\n")

    # Find all users
    users_dir = Path("data") / "users"

    if not users_dir.exists():
        console.print("[red]No users directory found![/red]")
        return

    users = [d.name for d in users_dir.iterdir() if d.is_dir()]

    if not users:
        console.print("[yellow]No users found[/yellow]")
        return

    console.print(f"Found {len(users)} user(s): {', '.join(users)}\n")

    # Dry run first
    console.print("[bold]Running dry run (no changes)...[/bold]\n")
    for user_id in users:
        migrate_user_qubes(user_id, dry_run=True)

    # Ask for confirmation
    console.print()
    if not Confirm.ask("[bold]Proceed with migration?[/bold]", default=False):
        console.print("[yellow]Migration cancelled[/yellow]")
        return

    # Actual migration
    console.print("\n[bold]Starting migration...[/bold]")
    for user_id in users:
        migrate_user_qubes(user_id, dry_run=False)

    console.print("\n[bold green]Migration complete![/bold green]")
    console.print("\nBackups saved to: [cyan]data/users/{user}/backups/[/cyan]")


if __name__ == "__main__":
    main()
