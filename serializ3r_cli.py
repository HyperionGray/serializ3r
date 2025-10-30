"""
Enhanced CLI for serializ3r with ML-based normalization support.
"""

import click
import sys
import os
from pathlib import Path


@click.group()
def cli():
    """
    serializ3r - Parse and normalize database leaks and credential dumps.
    
    Supports both traditional manual parsing and ML-based automatic normalization.
    """
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--min-confidence', default=0.5, type=float, 
              help='Minimum confidence threshold (0.0-1.0)')
@click.option('--use-ml', is_flag=True, default=True,
              help='Use ML-based normalization (default: True)')
@click.option('--verbose', is_flag=True, help='Verbose output')
def normalize(input_file, output_file, min_confidence, use_ml, verbose):
    """
    Normalize a credential dump file to JSONL format.
    
    Uses ML-based parsing to handle poorly formatted credential dumps
    with various formats, special characters, and noise.
    
    Example:
        serializ3r normalize dump.txt output.jsonl --min-confidence 0.7
    """
    try:
        from ml_normalizer import MLNormalizer
        import logging
        
        if verbose:
            logging.basicConfig(level=logging.INFO)
        
        click.echo(f"Processing: {input_file}")
        click.echo(f"Output: {output_file}")
        click.echo(f"Minimum confidence: {min_confidence}")
        
        normalizer = MLNormalizer(use_language_model=False)  # LM support not yet implemented
        
        with click.progressbar(length=100, label='Normalizing') as bar:
            stats = normalizer.normalize_file(input_file, output_file, min_confidence)
            bar.update(100)
        
        click.echo("\n✓ Processing complete!")
        click.echo(f"  Total lines processed: {stats['total_lines']}")
        click.echo(f"  Valid credentials extracted: {stats['valid_credentials']}")
        click.echo(f"  Filtered (low confidence): {stats['filtered_low_confidence']}")
        
        if stats['errors'] > 0:
            click.echo(f"  ⚠ Errors encountered: {stats['errors']}", err=True)
        
        success_rate = (stats['valid_credentials'] / stats['total_lines'] * 100) if stats['total_lines'] > 0 else 0
        click.echo(f"  Success rate: {success_rate:.1f}%")
        
    except ImportError:
        click.echo("Error: ML normalizer not available. Install dependencies with: pip install -r requirements.txt", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('input_pattern', type=str)
@click.argument('output_dir', type=click.Path())
@click.option('--min-confidence', default=0.5, type=float,
              help='Minimum confidence threshold (0.0-1.0)')
def batch_normalize(input_pattern, output_dir, min_confidence):
    """
    Batch normalize multiple credential dump files.
    
    Example:
        serializ3r batch-normalize "./dumps/*.txt" ./output/
    """
    import glob
    from ml_normalizer import MLNormalizer
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Find matching files
    files = glob.glob(input_pattern)
    
    if not files:
        click.echo(f"No files found matching pattern: {input_pattern}", err=True)
        sys.exit(1)
    
    click.echo(f"Found {len(files)} files to process")
    
    normalizer = MLNormalizer()
    total_stats = {'total_lines': 0, 'valid_credentials': 0, 'filtered_low_confidence': 0, 'errors': 0}
    
    with click.progressbar(files, label='Processing files') as bar:
        for input_file in bar:
            # Generate output filename
            base_name = Path(input_file).stem
            output_file = Path(output_dir) / f"{base_name}_normalized.jsonl"
            
            try:
                stats = normalizer.normalize_file(str(input_file), str(output_file), min_confidence)
                
                # Aggregate stats
                for key in total_stats:
                    total_stats[key] += stats[key]
            
            except Exception as e:
                click.echo(f"\n⚠ Error processing {input_file}: {e}", err=True)
    
    click.echo("\n✓ Batch processing complete!")
    click.echo(f"  Total lines processed: {total_stats['total_lines']}")
    click.echo(f"  Valid credentials extracted: {total_stats['valid_credentials']}")
    click.echo(f"  Filtered (low confidence): {total_stats['filtered_low_confidence']}")
    click.echo(f"  Errors: {total_stats['errors']}")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--lines', default=20, help='Number of lines to preview')
def preview(input_file, lines):
    """
    Preview the contents of a credential dump file.
    
    Shows first N lines with detected patterns highlighted.
    """
    from ml_normalizer import MLNormalizer, FeatureExtractor, LineClassifier
    
    click.echo(f"Preview of: {input_file}\n")
    
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, start=1):
            if i > lines:
                break
            
            line = line.strip()
            if not line:
                continue
            
            # Analyze line
            features = FeatureExtractor.extract_features(line)
            line_type, confidence = LineClassifier.classify(line, features)
            
            # Color code based on type
            if line_type.value == 'valid_credential':
                marker = "✓"
                color = 'green'
            else:
                marker = "✗"
                color = 'red'
            
            click.echo(f"{i:3d} [{marker}] ", nl=False)
            click.secho(line[:80], fg=color)
    
    click.echo(f"\nShowing first {min(lines, i)} lines")


@cli.command()
def interactive():
    """
    Interactive mode for manual credential dump parsing.
    
    Legacy mode from original serializ3r implementation.
    """
    click.echo('=== Interactive Mode ===')
    click.echo('This is the legacy interactive parsing mode.')
    click.echo('For better results, use: serializ3r normalize <input> <output>')
    click.echo()
    
    database_location = click.prompt('Please enter the location of your dump', type=str)
    
    if not os.path.exists(database_location):
        click.echo(f"Error: File not found: {database_location}", err=True)
        sys.exit(1)
    
    # Read first five lines and print to user
    click.echo("\nFirst 5 lines of the file:")
    click.echo("-" * 50)
    
    with open(database_location, 'r', encoding='utf-8', errors='replace') as database_file:
        for i, line in enumerate(database_file):
            if i >= 5:
                break
            click.echo(line.rstrip())
    
    click.echo("-" * 50)
    
    # Ask user if json, csv, or other
    db_type = click.prompt(
        'Is the database in json format[1], csv format[2], or other[3]?',
        type=click.IntRange(1, 3)
    )
    
    db_types = {
        1: "Json",
        2: "CSV",
        3: "Other"
    }
    
    output = "The database is in " + db_types.get(db_type, "Invalid Type") + " Format"
    click.echo(output)
    
    click.echo("\nNote: Full conversion support coming soon!")
    click.echo("Recommendation: Use 'serializ3r normalize' for automatic parsing")


@cli.command()
def info():
    """
    Display information about the ML normalizer.
    """
    click.echo("serializ3r - ML-Based Credential Dump Normalizer")
    click.echo("=" * 50)
    click.echo()
    click.echo("Features:")
    click.echo("  • Classical ML-based line classification")
    click.echo("  • Automatic delimiter detection")
    click.echo("  • Hash type identification (MD5, SHA1, SHA256, bcrypt, etc.)")
    click.echo("  • Email, username, and password extraction")
    click.echo("  • Robust handling of malformed data")
    click.echo("  • JSONL output format")
    click.echo()
    click.echo("Supported Hash Types:")
    click.echo("  • MD5, SHA1, SHA256, SHA512")
    click.echo("  • bcrypt, NTLM")
    click.echo()
    click.echo("Supported Formats:")
    click.echo("  • email:password")
    click.echo("  • email:hash")
    click.echo("  • username:password")
    click.echo("  • email:username:password")
    click.echo("  • email:username:hash")
    click.echo("  • And many more variations with different delimiters")
    click.echo()
    click.echo("For more information, see: ML_NORMALIZATION_PLAN.md")


if __name__ == '__main__':
    cli()
