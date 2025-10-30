# Usage Examples and Demonstrations

This document provides practical examples of using the ML-based credential dump normalizer.

## Example 1: Basic Email:Password Format

### Input File (`simple.txt`)
```
user@example.com:password123
admin@company.com:Admin@2024
john.doe@test.org:mySecret!Pass
```

### Command
```bash
python serializ3r_cli.py normalize simple.txt output.jsonl
```

### Output (`output.jsonl`)
```jsonl
{"email": "user@example.com", "password": "password123", "confidence": 0.9, "line_number": 1, "detected_format": "email:password"}
{"email": "admin@company.com", "password": "Admin@2024", "confidence": 0.9, "line_number": 2, "detected_format": "email:password"}
{"email": "john.doe@test.org", "password": "mySecret!Pass", "confidence": 0.9, "line_number": 3, "detected_format": "email:password"}
```

## Example 2: Mixed Hash Types

### Input File (`hashes.txt`)
```
user1@example.com:5f4dcc3b5aa765d61d8327deb882cf99
user2@example.com:5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8
user3@example.com:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8
admin@test.com:$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
```

### Command
```bash
python serializ3r_cli.py normalize hashes.txt output.jsonl
```

### Output
```jsonl
{"email": "user1@example.com", "password_hash": "5f4dcc3b5aa765d61d8327deb882cf99", "hash_type": "md5", "confidence": 1.0, "line_number": 1, "detected_format": "email:hash"}
{"email": "user2@example.com", "password_hash": "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8", "hash_type": "sha1", "confidence": 1.0, "line_number": 2, "detected_format": "email:hash"}
{"email": "user3@example.com", "password_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", "hash_type": "sha256", "confidence": 1.0, "line_number": 3, "detected_format": "email:hash"}
{"email": "admin@test.com", "password_hash": "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy", "hash_type": "bcrypt", "confidence": 1.0, "line_number": 4, "detected_format": "email:hash"}
```

**Note**: The normalizer automatically identifies MD5 (32 hex), SHA1 (40 hex), SHA256 (64 hex), and bcrypt patterns!

## Example 3: Messy Real-World Data

### Input File (`messy_breach.txt`)
```
=====================================
ACME Corp Database Leak - Jan 2024
=====================================
Email:Password
------------------
user@acme.com:password1
admin@acme.com:admin123
# Some corrupt data follows
@@@##$$$%%%
developer@acme.com:devPass2024
# More credentials
manager|mgr123|5f4dcc3b5aa765d61d8327deb882cf99
------------------
Total: 4 valid entries
```

### Command
```bash
python serializ3r_cli.py normalize messy_breach.txt clean.jsonl --min-confidence 0.7
```

### Output
The normalizer will:
- ✅ Skip separator lines (`===`, `---`)
- ✅ Skip header lines ("ACME Corp...", "Email:Password")
- ✅ Skip garbage lines (`@@@##$$$%%%`)
- ✅ Extract valid credentials
- ✅ Handle different delimiters (`:` and `|`)
- ✅ Identify hash types automatically

Result: Clean JSONL with only valid credentials!

## Example 4: Multiple Delimiters

### Input File (`various_delims.txt`)
```
user1@example.com:password1
user2@example.com|password2
user3@example.com;password3
user4@example.com	password4
user5@example.com -- password5
```

### Command
```bash
python serializ3r_cli.py normalize various_delims.txt output.jsonl
```

### Output
All entries are correctly parsed despite different delimiters (`:`, `|`, `;`, tab, `--`)!

## Example 5: Username:Password Format

### Input File (`usernames.txt`)
```
john_doe:secretpass
admin_user:adminpass123
test.user:testpass
developer:dev@Pass2024
```

### Output
```jsonl
{"username": "john_doe", "password": "secretpass", "confidence": 0.6, "line_number": 1, "detected_format": "username:password"}
{"username": "admin_user", "password": "adminpass123", "confidence": 0.7, "line_number": 2, "detected_format": "username:password"}
{"username": "test.user", "password": "testpass", "confidence": 0.6, "line_number": 3, "detected_format": "username:password"}
{"username": "developer", "password": "dev@Pass2024", "confidence": 0.7, "line_number": 4, "detected_format": "username:password"}
```

## Example 6: Complex Multi-Field Format

### Input File (`complex.txt`)
```
user@example.com:john_doe:password123
admin@test.com:admin:5f4dcc3b5aa765d61d8327deb882cf99
```

### Output
```jsonl
{"email": "user@example.com", "username": "john_doe", "password": "password123", "confidence": 0.9, "line_number": 1, "detected_format": "email:username:password"}
{"email": "admin@test.com", "username": "admin", "password_hash": "5f4dcc3b5aa765d61d8327deb882cf99", "hash_type": "md5", "confidence": 1.0, "line_number": 2, "detected_format": "email:username:hash"}
```

## Example 7: Preview Mode

### Command
```bash
python serializ3r_cli.py preview messy_breach.txt --lines 15
```

### Output
```
Preview of: messy_breach.txt

  1 [✗] =====================================
  2 [✗] ACME Corp Database Leak - Jan 2024
  3 [✗] =====================================
  4 [✗] Email:Password
  5 [✗] ------------------
  6 [✓] user@acme.com:password1
  7 [✓] admin@acme.com:admin123
  8 [✗] # Some corrupt data follows
  9 [✗] @@@##$$$%%%
 10 [✓] developer@acme.com:devPass2024
 11 [✗] # More credentials
 12 [✓] manager|mgr123|5f4dcc3b5aa765d61d8327deb882cf99
 13 [✗] ------------------

Showing first 15 lines
```

**✓** = Valid credential detected  
**✗** = Noise/garbage/header

## Example 8: Batch Processing

### Directory Structure
```
breach_dumps/
├── acme_leak.txt
├── company_b_dump.txt
└── test_data.txt
```

### Command
```bash
python serializ3r_cli.py batch-normalize "./breach_dumps/*.txt" ./normalized/
```

### Result
```
Found 3 files to process
Processing files  [####################################]  100%

✓ Batch processing complete!
  Total lines processed: 423
  Valid credentials extracted: 287
  Filtered (low confidence): 12
  Errors: 3
```

### Output Files Created
```
normalized/
├── acme_leak_normalized.jsonl
├── company_b_dump_normalized.jsonl
└── test_data_normalized.jsonl
```

## Example 9: Python API Usage

### Script (`process_dumps.py`)
```python
from ml_normalizer import MLNormalizer

# Initialize normalizer
normalizer = MLNormalizer()

# Process single line
line = "user@example.com:password123"
entry = normalizer.normalize_line(line, line_number=1)

if entry:
    print(f"Found credential:")
    print(f"  Email: {entry.email}")
    print(f"  Password: {entry.password}")
    print(f"  Confidence: {entry.confidence:.2f}")
    print(f"  Format: {entry.detected_format}")

# Process entire file
print("\nProcessing file...")
stats = normalizer.normalize_file(
    input_path="breach.txt",
    output_path="clean.jsonl",
    min_confidence=0.7
)

print(f"\nResults:")
print(f"  Lines processed: {stats['total_lines']}")
print(f"  Valid credentials: {stats['valid_credentials']}")
print(f"  Success rate: {stats['valid_credentials']/stats['total_lines']*100:.1f}%")
```

### Output
```
Found credential:
  Email: user@example.com
  Password: password123
  Confidence: 0.90
  Format: email:password

Processing file...

Results:
  Lines processed: 150
  Valid credentials: 98
  Success rate: 65.3%
```

## Example 10: Filtering by Confidence

### Low Confidence (0.3)
```bash
python serializ3r_cli.py normalize dump.txt output.jsonl --min-confidence 0.3
```
Result: More entries, but may include some false positives

### Medium Confidence (0.5) - Default
```bash
python serializ3r_cli.py normalize dump.txt output.jsonl --min-confidence 0.5
```
Result: Balanced precision and recall

### High Confidence (0.8)
```bash
python serializ3r_cli.py normalize dump.txt output.jsonl --min-confidence 0.8
```
Result: Only high-confidence credentials, fewer false positives

## Example 11: Working with Output

### Load JSONL in Python
```python
import json

credentials = []
with open('output.jsonl', 'r') as f:
    for line in f:
        cred = json.loads(line)
        credentials.append(cred)

# Filter by hash type
md5_creds = [c for c in credentials if c.get('hash_type') == 'md5']
print(f"Found {len(md5_creds)} MD5 hashes")

# Get all emails
emails = [c['email'] for c in credentials if 'email' in c]
print(f"Found {len(emails)} email addresses")

# High confidence only
high_conf = [c for c in credentials if c['confidence'] > 0.9]
print(f"Found {len(high_conf)} high-confidence entries")
```

### Convert to CSV
```python
import json
import csv

with open('output.jsonl', 'r') as infile, \
     open('output.csv', 'w', newline='') as outfile:
    
    # Collect all entries
    entries = [json.loads(line) for line in infile]
    
    if entries:
        # Write CSV
        writer = csv.DictWriter(outfile, fieldnames=entries[0].keys())
        writer.writeheader()
        writer.writerows(entries)

print("Converted to CSV!")
```

### Query with jq
```bash
# Count entries by hash type
cat output.jsonl | jq -r '.hash_type' | sort | uniq -c

# Get all emails with high confidence
cat output.jsonl | jq -r 'select(.confidence > 0.9) | .email'

# Extract only passwords (not hashes)
cat output.jsonl | jq -r 'select(.password != null) | .password'
```

## Tips and Best Practices

1. **Start with Preview**: Use `preview` to understand the file structure before processing
2. **Adjust Confidence**: Lower threshold for recall, higher for precision
3. **Batch Processing**: Process multiple files efficiently with `batch-normalize`
4. **Check Statistics**: Review success rates to gauge data quality
5. **Use JSONL**: Easy to process line-by-line, works with streaming
6. **Monitor Errors**: Check error count in output statistics
7. **Validate Results**: Sample check output for accuracy

## Common Use Cases

- **Security Research**: Analyze credential dumps for patterns
- **Breach Notification**: Quickly extract affected accounts
- **Password Analysis**: Study password patterns and hash types
- **Data Cleanup**: Convert messy dumps to structured format
- **Integration**: Feed normalized data to other security tools
- **Reporting**: Generate statistics on credential leaks

## Performance Tips

- Use batch processing for multiple files
- Set appropriate confidence thresholds
- Process large files will stream automatically
- Monitor memory usage with very large dumps (>1GB)
- Use parallel batch processing for massive datasets

## Conclusion

The ML-based normalizer handles real-world messy data automatically:
- ✅ Multiple formats and delimiters
- ✅ Various hash types
- ✅ Noise and garbage filtering
- ✅ High confidence scoring
- ✅ Structured JSONL output
- ✅ Batch processing capabilities

All with minimal configuration and maximum automation!
