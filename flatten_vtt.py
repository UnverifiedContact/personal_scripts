#!/usr/bin/env python3
"""
VTT Flattener - Command-line utility to extract spoken text from VTT files
Removes timestamps, metadata, and formatting, leaving only the actual spoken words.
"""

import argparse
import re
import sys


def parse_vtt_file(file_path):
    """
    Parse a VTT file and extract text content, removing timestamps and metadata.
    
    Args:
        file_path: Path to the VTT file
        
    Returns:
        List of text lines extracted from the VTT file
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = []
    in_cue = False
    cue_text = []
    
    # Pattern to match timestamp lines (supports both HH:MM:SS.mmm and MM:SS.mmm formats)
    # Also handles optional cue settings after the timestamp
    timestamp_pattern = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?\.\d{3}\s*-->\s*\d{1,2}:\d{2}(:\d{2})?\.\d{3}')
    
    # Pattern to match dialogue markers (e.g., ">> Speaker:")
    dialogue_pattern = re.compile(r'^\s*>>\s*')
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            if in_cue and cue_text:
                # End of cue, process accumulated text
                text = ' '.join(cue_text).strip()
                if text:
                    # Remove >> prefix if present
                    if dialogue_pattern.match(text):
                        text = dialogue_pattern.sub('', text).strip()
                    lines.append(text)
                cue_text = []
                in_cue = False
            continue
        
        # Skip WEBVTT header
        if line.upper() == 'WEBVTT':
            continue
        
        # Skip cue identifiers (e.g., "1", "2", "NOTE", etc.)
        # Can be numeric or all-caps words
        if re.match(r'^(\d+|[A-Z]+)$', line) and line.upper() != 'WEBVTT':
            continue
        
        # Skip timestamp lines (may have cue settings after timestamp)
        if timestamp_pattern.match(line):
            in_cue = True
            continue
        
        # Skip styling/metadata lines (lines starting with STYLE, NOTE, etc.)
        if re.match(r'^(STYLE|NOTE|REGION|KIND):', line, re.IGNORECASE):
            continue
        
        # If we're in a cue, collect the text
        if in_cue:
            # Remove VTT tags like <c>, <v>, <i>, <b>, <u>, etc.
            clean_line = re.sub(r'</?[cvibun]\b[^>]*>', '', line)
            # Remove speaker tags like <v Speaker>
            clean_line = re.sub(r'<v[^>]*>', '', clean_line)
            # Remove any remaining HTML-like tags
            clean_line = re.sub(r'<[^>]+>', '', clean_line)
            # Remove cue settings (e.g., "align:start position:10%")
            clean_line = re.sub(r'align:\w+\s+position:\d+%', '', clean_line)
            
            if clean_line.strip():
                cue_text.append(clean_line.strip())
    
    # Handle any remaining cue text
    if cue_text:
        text = ' '.join(cue_text).strip()
        if text:
            if dialogue_pattern.match(text):
                text = dialogue_pattern.sub('', text).strip()
            lines.append(text)
    
    # Fallback: if no lines extracted, try a more lenient extraction
    # This handles edge cases where VTT structure might be non-standard
    if not lines:
        for line in content.split('\n'):
            line = line.strip()
            # Skip empty lines, headers, and obvious metadata
            if not line or line.upper() == 'WEBVTT' or timestamp_pattern.match(line):
                continue
            # Skip cue identifiers and metadata markers
            if re.match(r'^(\d+|[A-Z]+)$', line) or re.match(r'^(STYLE|NOTE|REGION|KIND):', line, re.IGNORECASE):
                continue
            # Try to extract any text-like content
            clean_line = re.sub(r'<[^>]+>', '', line)  # Remove HTML tags
            clean_line = re.sub(r'align:\w+\s+position:\d+%', '', clean_line)  # Remove cue settings
            if clean_line.strip() and len(clean_line.strip()) > 1:
                lines.append(clean_line.strip())
    
    return lines


def is_text_file(file_path):
    """
    Quick check to verify file is text-based (not binary).
    Reads first 8KB and checks for null bytes.
    Very lenient - only rejects obvious binary files.
    
    Args:
        file_path: Path to file to check
        
    Returns:
        True if file appears to be text, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)  # Read first 8KB
            
        # Check for null bytes (binary files typically have them)
        # This is the main indicator - text files shouldn't have null bytes
        if b'\x00' in chunk:
            return False
        
        # If no null bytes, assume it's text (very lenient)
        # We'll let the actual parsing handle any encoding issues
        return True
    except IOError:
        return False


def flatten_vtt(input_file, output_file=None):
    """
    Flatten a VTT file, extracting only spoken text.
    
    Args:
        input_file: Path to input VTT file
        output_file: Optional path to output file. If None, prints to stdout.
        
    Returns:
        Flattened text as a string
    """
    lines = parse_vtt_file(input_file)
    flattened_text = '\n'.join(lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(flattened_text)
        print(f"Flattened text written to: {output_file}", file=sys.stderr)
    else:
        print(flattened_text)
    
    return flattened_text


def main():
    parser = argparse.ArgumentParser(
        description='Extract spoken text from VTT files, removing timestamps and metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s video.vtt                    # Write to video_flattened.txt
  %(prog)s video.vtt -o output.txt      # Write to custom output file
  %(prog)s video.vtt --output output.txt # Alternative syntax
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Path to the input VTT file'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Path to output file (default: <input>_flattened.txt in same directory)'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    import os
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        return 1
    
    if not os.path.isfile(args.input_file):
        print(f"Error: Input path is not a file: {args.input_file}", file=sys.stderr)
        return 1
    
    # Quick check: verify file is text-based (not binary)
    if not is_text_file(args.input_file):
        print(f"Error: File does not appear to be a text file: {args.input_file}", file=sys.stderr)
        print("This script only processes text-based VTT files.", file=sys.stderr)
        return 1
    
    # Generate default output filename if not provided
    if not args.output_file:
        input_dir = os.path.dirname(args.input_file)
        input_basename = os.path.basename(args.input_file)
        input_name = os.path.splitext(input_basename)[0]
        args.output_file = os.path.join(input_dir, f"{input_name}_flattened.txt")
    
    flatten_vtt(args.input_file, args.output_file)
    return 0


if __name__ == '__main__':
    sys.exit(main())

