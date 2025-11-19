#!/usr/bin/env python3
"""
Project Reality Mortar Calculator - Map Collection Script
Extracts server.zip files from PR:BF2 installation and prepares them for GitHub upload.

This script is Phase 1 of the map processing workflow:
- Scans PR:BF2 installation for map files
- Validates and copies server.zip files
- Generates manifest with MD5 checksums
- Configures Git LFS if needed

Usage:
    python collect_maps.py                    # Auto-detect installation
    python collect_maps.py --path "D:\\Games\\PR"  # Custom path
"""

import os
import sys
import shutil
import zipfile
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# Default PR:BF2 installation paths to check
DEFAULT_PR_PATHS = [
    r"C:\Program Files (x86)\Project Reality\Project Reality BF2",
    r"D:\Games\Project Reality\Project Reality BF2",
    r"C:\Program Files\Project Reality\Project Reality BF2",
]

# Size threshold for Git LFS (in bytes)
LFS_THRESHOLD_MB = 10
LFS_THRESHOLD_BYTES = LFS_THRESHOLD_MB * 1024 * 1024


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def calculate_md5(file_path: Path) -> str:
    """Calculate MD5 checksum of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 checksum as hexadecimal string
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read in 64kb chunks to handle large files
        for chunk in iter(lambda: f.read(65536), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def validate_server_zip(zip_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate that server.zip is a valid zip file and contains heightmap.
    
    Args:
        zip_path: Path to server.zip file
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if valid, False otherwise
        - error_message: Error description if invalid, None if valid
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Check if zip file is corrupted
            bad_file = zf.testzip()
            if bad_file is not None:
                return False, f"Corrupted file in zip: {bad_file}"
            
            # Check for HeightmapPrimary.raw
            file_list = zf.namelist()
            has_heightmap = any('HeightmapPrimary.raw' in f for f in file_list)
            
            if not has_heightmap:
                return False, "Missing HeightmapPrimary.raw"
            
            return True, None
            
    except zipfile.BadZipFile:
        return False, "Not a valid zip file"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def find_pr_installation(custom_path: Optional[str] = None) -> Optional[Path]:
    """Find Project Reality installation directory.
    
    Args:
        custom_path: Optional custom installation path
        
    Returns:
        Path to PR installation, or None if not found
    """
    paths_to_check = []
    
    # Check custom path first
    if custom_path:
        paths_to_check.append(custom_path)
    
    # Then check default paths
    paths_to_check.extend(DEFAULT_PR_PATHS)
    
    for path_str in paths_to_check:
        path = Path(path_str)
        levels_dir = path / "levels"
        
        if path.exists() and levels_dir.exists():
            print(f"{Colors.GREEN}✓ Found PR:BF2 installation at: {path}{Colors.RESET}")
            return path
    
    return None


def discover_maps(pr_path: Path) -> List[Path]:
    """Discover all map folders in PR installation.
    
    Args:
        pr_path: Path to PR:BF2 installation
        
    Returns:
        List of paths to map folders containing server.zip
    """
    levels_dir = pr_path / "levels"
    map_folders = []
    
    if not levels_dir.exists():
        return map_folders
    
    # Scan all subdirectories
    for item in levels_dir.iterdir():
        if item.is_dir():
            server_zip = item / "server.zip"
            if server_zip.exists():
                map_folders.append(item)
    
    return sorted(map_folders)


def process_map(map_folder: Path, output_dir: Path, existing_manifest: Dict) -> Optional[Dict]:
    """Process a single map folder.
    
    Args:
        map_folder: Path to map folder in PR installation
        output_dir: Path to raw_map_data directory
        existing_manifest: Existing manifest data for duplicate checking
        
    Returns:
        Dict with map metadata, or None if processing failed
    """
    map_name = map_folder.name
    server_zip = map_folder / "server.zip"
    
    print(f"\n{Colors.BLUE}Processing: {map_name}{Colors.RESET}")
    
    # Validate zip file
    is_valid, error_msg = validate_server_zip(server_zip)
    if not is_valid:
        print(f"  {Colors.RED}✗ Validation failed: {error_msg}{Colors.RESET}")
        return None
    
    print(f"  {Colors.GREEN}✓ Validation passed{Colors.RESET}")
    
    # Calculate MD5 checksum
    print(f"  Calculating MD5 checksum...")
    md5_checksum = calculate_md5(server_zip)
    print(f"  MD5: {md5_checksum}")
    
    # Check for duplicate
    existing_maps = existing_manifest.get('maps', [])
    existing_map = next((m for m in existing_maps if m['name'] == map_name), None)
    
    if existing_map and existing_map.get('md5') == md5_checksum:
        print(f"  {Colors.YELLOW}⊙ Skipped (identical to existing){Colors.RESET}")
        return existing_map  # Return existing data
    
    # Create output directory
    map_output_dir = output_dir / map_name
    map_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy server.zip
    output_zip = map_output_dir / "server.zip"
    print(f"  Copying to {output_zip.relative_to(output_dir.parent)}...")
    shutil.copy2(server_zip, output_zip)
    
    # Get file size
    file_size = output_zip.stat().st_size
    
    print(f"  {Colors.GREEN}✓ Copied successfully ({file_size / 1024:.1f} KB){Colors.RESET}")
    
    # Return metadata
    return {
        'name': map_name,
        'md5': md5_checksum,
        'size_bytes': file_size,
        'collected_at': datetime.utcnow().isoformat() + 'Z',
        'source_path': str(map_folder),
        'status': 'updated' if existing_map else 'new'
    }


def generate_manifest(maps_data: List[Dict], output_dir: Path) -> None:
    """Generate manifest.json file.
    
    Args:
        maps_data: List of map metadata dictionaries
        output_dir: Path to raw_map_data directory
    """
    total_size = sum(m['size_bytes'] for m in maps_data)
    
    manifest = {
        'maps': maps_data,
        'total_maps': len(maps_data),
        'total_size_bytes': total_size,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'collection_date': datetime.utcnow().isoformat() + 'Z',
        'format_version': '1.0'
    }
    
    manifest_path = output_dir / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n{Colors.GREEN}✓ Generated manifest: {manifest_path}{Colors.RESET}")


def configure_git_lfs(total_size_bytes: int, repo_root: Path) -> None:
    """Configure Git LFS if needed.
    
    Args:
        total_size_bytes: Total size of collected files
        repo_root: Path to repository root
    """
    gitattributes_path = repo_root / '.gitattributes'
    
    # Check if LFS is needed
    if total_size_bytes < LFS_THRESHOLD_BYTES:
        print(f"\n{Colors.YELLOW}ⓘ Total size ({total_size_bytes / (1024*1024):.1f} MB) below {LFS_THRESHOLD_MB} MB threshold{Colors.RESET}")
        print(f"  Git LFS configuration optional")
        return
    
    print(f"\n{Colors.BLUE}Configuring Git LFS...{Colors.RESET}")
    
    # LFS patterns
    lfs_patterns = [
        '*.zip filter=lfs diff=lfs merge=lfs -text',
        '*.raw filter=lfs diff=lfs merge=lfs -text',
    ]
    
    # Read existing .gitattributes
    existing_content = ''
    if gitattributes_path.exists():
        with open(gitattributes_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    # Add LFS patterns if not present
    new_patterns = []
    for pattern in lfs_patterns:
        if pattern not in existing_content:
            new_patterns.append(pattern)
    
    if new_patterns:
        mode = 'a' if existing_content else 'w'
        with open(gitattributes_path, mode, encoding='utf-8') as f:
            if existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            f.write('\n# Project Reality Map Data (Git LFS)\n')
            for pattern in new_patterns:
                f.write(pattern + '\n')
        
        print(f"  {Colors.GREEN}✓ Updated .gitattributes with LFS patterns{Colors.RESET}")
        print(f"  {Colors.YELLOW}⚠ Run 'git lfs install' if not already configured{Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}✓ LFS patterns already configured{Colors.RESET}")


def generate_report(maps_data: List[Dict], errors: List[str], output_dir: Path) -> None:
    """Generate collection report.
    
    Args:
        maps_data: List of successfully processed maps
        errors: List of error messages
        output_dir: Path to processor directory
    """
    report_lines = []
    report_lines.append("="*70)
    report_lines.append("PROJECT REALITY MORTAR CALCULATOR - MAP COLLECTION REPORT")
    report_lines.append("="*70)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Summary
    new_maps = [m for m in maps_data if m.get('status') == 'new']
    updated_maps = [m for m in maps_data if m.get('status') == 'updated']
    skipped_maps = [m for m in maps_data if m.get('status') not in ['new', 'updated']]
    
    report_lines.append("SUMMARY:")
    report_lines.append(f"  Total maps found: {len(maps_data) + len(errors)}")
    report_lines.append(f"  ✓ Successfully collected: {len(maps_data)}")
    report_lines.append(f"    - New maps: {len(new_maps)}")
    report_lines.append(f"    - Updated maps: {len(updated_maps)}")
    report_lines.append(f"    - Unchanged (skipped): {len(skipped_maps)}")
    report_lines.append(f"  ✗ Errors: {len(errors)}")
    report_lines.append("")
    
    # Collected maps
    if maps_data:
        report_lines.append("COLLECTED MAPS:")
        for map_data in sorted(maps_data, key=lambda x: x['name']):
            status_icon = "+" if map_data.get('status') == 'new' else "↻" if map_data.get('status') == 'updated' else "="
            size_kb = map_data['size_bytes'] / 1024
            report_lines.append(f"  [{status_icon}] {map_data['name']:<30} {size_kb:>8.1f} KB  {map_data['md5'][:8]}")
        report_lines.append("")
    
    # Errors
    if errors:
        report_lines.append("ERRORS:")
        for error in errors:
            report_lines.append(f"  ✗ {error}")
        report_lines.append("")
    
    # File paths
    report_lines.append("OUTPUT:")
    report_lines.append(f"  Data directory: raw_map_data/")
    report_lines.append(f"  Manifest: raw_map_data/manifest.json")
    report_lines.append("")
    
    # Next steps
    report_lines.append("NEXT STEPS:")
    report_lines.append("  1. Review this report for any errors")
    report_lines.append("  2. Commit changes: git add raw_map_data/ .gitattributes")
    report_lines.append("  3. Commit: git commit -m 'chore: collect maps - [count] maps'")
    report_lines.append("  4. Push to GitHub: git push")
    report_lines.append("  5. Run processor/process_maps.ipynb to process maps")
    report_lines.append("="*70)
    
    report_content = '\n'.join(report_lines)
    
    # Print to console
    print("\n" + report_content)
    
    # Save to file
    report_path = output_dir / 'collection_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n{Colors.GREEN}✓ Report saved to: {report_path}{Colors.RESET}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Collect server.zip files from PR:BF2 installation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python collect_maps.py                      # Auto-detect installation
  python collect_maps.py --path "D:\\Games\\PR"  # Custom path
        """
    )
    parser.add_argument(
        '--path',
        type=str,
        help='Custom path to PR:BF2 installation'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='raw_map_data',
        help='Output directory (default: raw_map_data)'
    )
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}PROJECT REALITY MORTAR CALCULATOR - Map Collection{Colors.RESET}")
    print("="*70)
    
    # Find repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    # Find PR installation
    pr_path = find_pr_installation(args.path)
    
    if pr_path is None:
        print(f"\n{Colors.RED}✗ Could not find PR:BF2 installation{Colors.RESET}")
        print(f"\nSearched paths:")
        for path in DEFAULT_PR_PATHS:
            print(f"  - {path}")
        print(f"\nPlease specify custom path with --path argument")
        sys.exit(1)
    
    # Discover maps
    print(f"\n{Colors.BLUE}Discovering maps...{Colors.RESET}")
    map_folders = discover_maps(pr_path)
    
    if not map_folders:
        print(f"{Colors.RED}✗ No maps found in {pr_path / 'levels'}{Colors.RESET}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}✓ Found {len(map_folders)} maps{Colors.RESET}")
    
    # Create output directory
    output_dir = repo_root / args.output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load existing manifest if present
    manifest_path = output_dir / 'manifest.json'
    existing_manifest = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                existing_manifest = json.load(f)
            print(f"\n{Colors.BLUE}Loaded existing manifest ({existing_manifest.get('total_maps', 0)} maps){Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.YELLOW}⚠ Could not load existing manifest: {e}{Colors.RESET}")
    
    # Process maps
    print(f"\n{Colors.BOLD}Processing maps...{Colors.RESET}")
    maps_data = []
    errors = []
    
    for i, map_folder in enumerate(map_folders, 1):
        try:
            print(f"\n[{i}/{len(map_folders)}]", end=" ")
            map_metadata = process_map(map_folder, output_dir, existing_manifest)
            
            if map_metadata:
                maps_data.append(map_metadata)
        except Exception as e:
            error_msg = f"{map_folder.name}: {str(e)}"
            errors.append(error_msg)
            print(f"  {Colors.RED}✗ Error: {e}{Colors.RESET}")
    
    # Generate manifest
    if maps_data:
        generate_manifest(maps_data, output_dir)
    
    # Configure Git LFS
    total_size = sum(m['size_bytes'] for m in maps_data)
    configure_git_lfs(total_size, repo_root)
    
    # Generate report
    generate_report(maps_data, errors, script_dir)
    
    # Exit code
    if errors:
        print(f"\n{Colors.YELLOW}⚠ Completed with {len(errors)} error(s){Colors.RESET}")
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Collection completed successfully!{Colors.RESET}")
        sys.exit(0)


if __name__ == '__main__':
    main()
