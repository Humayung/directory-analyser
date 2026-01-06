#!/usr/bin/env python3
"""
Directory Composition Analyzer

Analyzes a directory to find all file extensions, count files per extension,
and calculate total size per extension. Generates an HTML visualization with embedded data.
"""

import os
import json
import argparse
import webbrowser
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any


def get_file_extension(filepath: str) -> str:
    """Get file extension, returning 'no_extension' if none exists."""
    ext = Path(filepath).suffix.lower()
    return ext[1:] if ext else 'no_extension'


def analyze_directory(directory_path: str, show_progress: bool = True) -> Dict[str, Any]:
    """
    Analyze directory composition by file extension.
    
    Args:
        directory_path: Path to directory to analyze
        show_progress: Whether to show progress updates
        
    Returns:
        Dictionary containing analysis results
    """
    if not os.path.isdir(directory_path):
        raise ValueError(f"'{directory_path}' is not a valid directory")
    
    # Data structures to track statistics
    extension_stats = defaultdict(lambda: {'count': 0, 'total_size': 0})
    total_files = 0
    total_size = 0
    errors = []
    
    # Walk through directory
    if show_progress:
        print(f"Analyzing directory: {directory_path}")
        print("Scanning files...")
    
    try:
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                try:
                    # Get file size
                    file_size = os.path.getsize(filepath)
                    
                    # Get extension
                    ext = get_file_extension(filename)
                    
                    # Update statistics
                    extension_stats[ext]['count'] += 1
                    extension_stats[ext]['total_size'] += file_size
                    total_files += 1
                    total_size += file_size
                    
                    # Show progress every 1000 files
                    if show_progress and total_files % 1000 == 0:
                        print(f"  Processed {total_files:,} files...", end='\r')
                        
                except (OSError, PermissionError) as e:
                    errors.append({
                        'file': filepath,
                        'error': str(e)
                    })
                    continue
    
    except KeyboardInterrupt:
        if show_progress:
            print("\n\nAnalysis interrupted by user.")
        raise
    
    if show_progress:
        print(f"\n  Completed! Processed {total_files:,} files")
    
    # Convert defaultdict to regular dict and format results
    extension_data = {}
    for ext, stats in sorted(extension_stats.items()):
        extension_data[ext] = {
            'count': stats['count'],
            'total_size': stats['total_size'],
            'total_size_mb': round(stats['total_size'] / (1024 * 1024), 2),
            'total_size_gb': round(stats['total_size'] / (1024 * 1024 * 1024), 2)
        }
    
    # Build result dictionary
    result = {
        'directory': os.path.abspath(directory_path),
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'unique_extensions': len(extension_stats)
        },
        'extensions': extension_data
    }
    
    if errors:
        result['errors'] = errors
        result['error_count'] = len(errors)
    
    return result


def generate_html_with_data(html_template_path: str, json_data: Dict[str, Any], output_html_path: str) -> str:
    """
    Generate HTML file with JSON data embedded as a JavaScript variable.
    
    Args:
        html_template_path: Path to the HTML template file
        json_data: The analysis data dictionary to embed
        output_html_path: Path where the output HTML will be saved
        
    Returns:
        Path to the generated HTML file
    """
    # Read the HTML template
    with open(html_template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Convert JSON data to a JavaScript variable
    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
    
    # Replace the loadData function to use embedded data
    # Find the exact function text and replace it
    old_function = '''        // Load JSON file
        async function loadData() {
            try {
                // Get JSON filename from URL parameter or use default
                const urlParams = new URLSearchParams(window.location.search);
                const jsonFile = urlParams.get('json') || 'photos_analysis.json';
                
                const response = await fetch(jsonFile);
                if (!response.ok) {
                    throw new Error(`Failed to load analysis data from ${jsonFile}`);
                }
                analysisData = await response.json();
                displayData();
            } catch (error) {
                document.getElementById('loading').innerHTML = 
                    `<div style="color: #ef4444;">Error: ${error.message}</div>`;
            }
        }'''
    
    replacement = f'''        // Embedded analysis data
        const embeddedAnalysisData = {json_str};
        
        // Load embedded data
        function loadData() {{
            try {{
                analysisData = embeddedAnalysisData;
                displayData();
            }} catch (error) {{
                document.getElementById('loading').innerHTML = 
                    `<div style="color: #ff6b6b;">Error: ${{error.message}}</div>`;
            }}
        }}'''
    
    if old_function in html_content:
        html_content = html_content.replace(old_function, replacement)
    else:
        # Fallback: use regex if exact match fails
        import re
        pattern = r'// Load JSON file.*?async function loadData\(\) \{.*?\n\s*\}'
        html_content = re.sub(pattern, replacement.strip(), html_content, flags=re.DOTALL)
    
    # Write the new HTML file
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_html_path


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Analyze directory composition by file extension',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_directory.py /path/to/directory
  python analyze_directory.py /path/to/directory --no-open
  python analyze_directory.py /path/to/directory --html-template /path/to/template.html
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        help='Path to directory to analyze'
    )
    
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress output'
    )
    
    parser.add_argument(
        '--no-open',
        action='store_true',
        help='Do not automatically open the HTML visualization'
    )
    
    parser.add_argument(
        '--html-template',
        type=str,
        default=None,
        help='Path to HTML template file (default: visualize_analysis.html in current directory)'
    )
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist.")
        return 1
    
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory.")
        return 1
    
    try:
        # Analyze directory
        results = analyze_directory(args.directory, show_progress=not args.no_progress)
        
        if not args.no_progress:
            print("\nAnalysis complete!")
            print(f"\nSummary:")
            print(f"  Total files: {results['summary']['total_files']:,}")
            print(f"  Total size: {results['summary']['total_size_gb']:.2f} GB ({results['summary']['total_size_mb']:.2f} MB)")
            print(f"  Unique extensions: {results['summary']['unique_extensions']}")
            if 'error_count' in results:
                print(f"  Errors encountered: {results['error_count']}")
        
        # Generate HTML with embedded data and open if requested
        if not args.no_open:
            # Find HTML template
            if args.html_template:
                html_template_path = args.html_template
            else:
                # Look for template in current working directory first
                html_template_path = os.path.join(os.getcwd(), 'visualize_analysis.html')
                
                # If not found, try script directory
                if not os.path.exists(html_template_path):
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    html_template_path = os.path.join(script_dir, 'visualize_analysis.html')
            
            if os.path.exists(html_template_path):
                # Generate output HTML filename based on directory name
                dir_name = os.path.basename(os.path.abspath(args.directory))
                if not dir_name:
                    # Handle root directory case
                    dir_name = os.path.basename(os.path.dirname(os.path.abspath(args.directory)))
                # Clean up directory name for filename (remove spaces, special chars)
                safe_dir_name = "".join(c for c in dir_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_dir_name = safe_dir_name.replace(' ', '_')
                if not safe_dir_name:
                    safe_dir_name = "analysis"
                
                # Save HTML in the target directory (the directory being analyzed)
                target_dir = os.path.abspath(args.directory)
                output_html_path = os.path.join(target_dir, f'directory_visualization.html')
                
                if not args.no_progress:
                    print(f"\nGenerating HTML visualization with embedded data...")
                
                try:
                    # Generate HTML with embedded JSON data
                    generate_html_with_data(html_template_path, results, output_html_path)
                    
                    if not args.no_progress:
                        print(f"HTML visualization generated: {output_html_path}")
                        print("Opening in browser...")
                    
                    # Open the generated HTML file
                    webbrowser.open(f'file://{os.path.abspath(output_html_path)}')
                    
                except Exception as e:
                    if not args.no_progress:
                        print(f"\nError generating HTML visualization: {e}")
            else:
                if not args.no_progress:
                    print(f"\nNote: HTML template not found. Expected at: {html_template_path}")
                    print("Skipping HTML generation.")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    exit(main())

