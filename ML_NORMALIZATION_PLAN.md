# ML-Based Credential Dump Normalization Plan

## Executive Summary

This document outlines a comprehensive plan for implementing a hybrid ML approach to parse and normalize poorly formatted credential dumps into standardized JSONL files. The solution combines classical machine learning techniques with small language models to handle messy, malformed data that often contains adversarial characters designed to break parsers.

## Problem Statement

Credential dumps from data breaches are:
- **Highly inconsistent**: Multiple formats (email:password, username|hash, etc.)
- **Adversarially formatted**: Contains special characters, encodings, and obfuscation
- **Mixed content**: Comments, headers, footers, garbage data mixed with valid credentials
- **Time-consuming**: Manual parsing and cleaning currently required
- **Critical for security**: Organizations need quick alerts about credential leaks

## Proposed Architecture

### Phase 1: Classical ML Feature Extraction

**Purpose**: Quickly identify and classify lines/blocks of text

**Components**:

1. **Pattern Recognition Engine**
   - Regular expression library for common patterns (email, hash types, usernames)
   - Fuzzy matching for partially corrupted data
   - Statistical analysis of character distributions
   
2. **Feature Extractor**
   - Line length statistics
   - Character type ratios (alphanumeric, special chars, whitespace)
   - Delimiter detection (`:`, `|`, `;`, `,`, `\t`, etc.)
   - Hash type identification (MD5, SHA1, SHA256, bcrypt, etc.)
   - Email domain extraction
   - Entropy calculation (to detect garbage vs. valid data)

3. **Classifier**
   - Random Forest or Gradient Boosting for line classification
   - Categories: valid_credential, header, footer, comment, garbage, separator
   - Training on labeled examples of credential dump formats

### Phase 2: Small Language Model Integration

**Purpose**: Handle ambiguous cases and context-dependent parsing

**Recommended Model**: DistilBERT or similar small transformer (~66M parameters)

**Fine-tuning Strategy**:
- Pre-train on synthetic credential dump data
- Fine-tune on real-world examples (anonymized)
- Task: Sequence labeling (token classification)
- Labels: EMAIL, USERNAME, PASSWORD, HASH, SALT, DOMAIN, NOISE, DELIMITER

**Advantages**:
- Context-aware parsing
- Handles typos and malformed entries
- Can learn domain-specific patterns
- Relatively lightweight (~250MB model)

### Phase 3: Multi-Stage Parsing Pipeline

```
Input File
    ↓
1. Pre-processing
    - Encoding detection & normalization (UTF-8, Latin-1, etc.)
    - Line splitting with robust error handling
    - Remove null bytes and control characters
    ↓
2. Classical ML Filtering
    - Remove obvious garbage lines (entropy too high/low)
    - Classify lines by type
    - Extract basic features
    ↓
3. Field Extraction
    - Delimiter detection per line
    - Split into candidate fields
    - Apply regex patterns
    ↓
4. LM Refinement (for ambiguous cases)
    - Token classification
    - Context-based field identification
    - Confidence scoring
    ↓
5. Normalization
    - Standardize field names
    - Hash type identification
    - Email validation
    - Username cleaning
    ↓
6. JSONL Output
    - Structured format: {"email": "...", "username": "...", "password": "...", "hash": "...", ...}
    - Metadata: source_line_number, confidence_score, detected_format
```

## Technical Implementation Details

### Dependencies
- **Classical ML**: scikit-learn, numpy, pandas
- **NLP/LM**: transformers (HuggingFace), torch
- **Utilities**: chardet (encoding detection), tqdm (progress bars), click (CLI)
- **Data**: jsonlines (JSONL I/O)

### Data Structures

```python
class CredentialEntry:
    email: Optional[str]
    username: Optional[str]
    password: Optional[str]
    password_hash: Optional[str]
    hash_type: Optional[str]
    salt: Optional[str]
    additional_fields: Dict[str, str]
    metadata: Dict[str, Any]  # confidence, line_number, detected_format
```

### Robustness Features

1. **Encoding Handling**
   - Auto-detect encoding with chardet
   - Fallback chain: UTF-8 → Latin-1 → Windows-1252 → ASCII (ignore errors)

2. **Adversarial Character Handling**
   - Strip null bytes, excessive whitespace
   - Normalize Unicode variations
   - Detect and remove zero-width characters
   - Handle escaped characters

3. **Error Recovery**
   - Continue processing on malformed lines
   - Log problematic entries separately
   - Provide summary statistics

4. **Performance Optimization**
   - Batch processing for LM inference
   - Parallel processing for classical ML features
   - Streaming mode for large files
   - Memory-efficient chunking

## Training Data Strategy

### Synthetic Data Generation
- Create synthetic credential dumps with various formats
- Add controlled noise and adversarial characters
- Mix valid and invalid entries

### Real-World Data
- Collect anonymized samples from public breach databases (HaveIBeenPwned format)
- Manual labeling of diverse examples
- Community contributions (with privacy considerations)

### Augmentation
- Character substitution (e.g., @ → (at))
- Encoding variations
- Delimiter variations
- Random noise injection

## Evaluation Metrics

1. **Precision**: % of extracted credentials that are valid
2. **Recall**: % of actual credentials successfully extracted
3. **F1 Score**: Harmonic mean of precision and recall
4. **Format Detection Accuracy**: % of correctly identified formats
5. **Processing Speed**: Lines per second
6. **Robustness**: % of successfully processed files with errors

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Setup project structure
- [ ] Implement encoding detection and normalization
- [ ] Create robust line parsing with error handling
- [ ] Build pattern recognition library

### Phase 2: Classical ML Components (Week 2-3)
- [ ] Implement feature extraction
- [ ] Create line classifier
- [ ] Build delimiter detection
- [ ] Add hash type identification

### Phase 3: LM Integration (Week 3-4)
- [ ] Select and prepare small language model
- [ ] Create training data pipeline
- [ ] Fine-tune model on credential parsing task
- [ ] Integrate with main pipeline

### Phase 4: Testing & Refinement (Week 4-5)
- [ ] Create test suite with diverse examples
- [ ] Benchmark performance
- [ ] Optimize processing speed
- [ ] Handle edge cases

### Phase 5: Documentation & Deployment (Week 5-6)
- [ ] Write comprehensive documentation
- [ ] Create usage examples
- [ ] Package for distribution
- [ ] Deploy model artifacts

## Usage Example

```bash
# Basic usage
python serializ3r.py normalize input.txt output.jsonl

# With ML model
python serializ3r.py normalize input.txt output.jsonl --use-ml

# Batch processing
python serializ3r.py normalize-batch ./dumps/*.txt ./output/

# With confidence threshold
python serializ3r.py normalize input.txt output.jsonl --min-confidence 0.8
```

## Expected Output Format

```jsonl
{"email": "user@example.com", "password": "plaintext123", "hash_type": null, "confidence": 0.95, "line": 1, "format": "email:password"}
{"email": "admin@test.com", "username": "admin", "password_hash": "5f4dcc3b5aa765d61d8327deb882cf99", "hash_type": "md5", "confidence": 0.98, "line": 2, "format": "email:username:hash"}
{"username": "john_doe", "password": "secretpass", "confidence": 0.87, "line": 5, "format": "username:password"}
```

## Risk Mitigation

1. **Privacy**: Never log or store actual passwords/credentials
2. **False Positives**: Use confidence thresholds to filter uncertain matches
3. **Model Bias**: Diverse training data to avoid format-specific biases
4. **Performance**: Optimize with caching and parallel processing
5. **Maintenance**: Modular design for easy updates to patterns and models

## Alternative Approaches Considered

1. **Pure Rule-Based**: Too brittle for adversarial content
2. **Large Language Models (GPT-3/4)**: Too expensive, privacy concerns, overkill
3. **Pure Classical ML**: Lacks context understanding for ambiguous cases
4. **Manual Parsing**: Not scalable, current pain point

## Conclusion

This hybrid approach leverages the speed and efficiency of classical ML for obvious cases while using small language models for ambiguous, context-dependent parsing. The solution is:
- **Robust**: Handles adversarial formatting and encoding issues
- **Efficient**: Fast processing with batching and optimization
- **Accurate**: High precision/recall through dual-approach validation
- **Maintainable**: Modular design with clear separation of concerns
- **Scalable**: Can process large dumps with streaming/chunking

The estimated development time is 5-6 weeks for a production-ready implementation, with continuous improvements possible as more training data becomes available.
