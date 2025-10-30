"""
ML-based credential dump normalizer.

This module implements a hybrid approach combining classical ML and small language models
to parse poorly formatted credential dumps into normalized JSONL format.
"""

import re
import json
import hashlib
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LineType(Enum):
    """Classification of line types in credential dumps."""
    VALID_CREDENTIAL = "valid_credential"
    HEADER = "header"
    FOOTER = "footer"
    COMMENT = "comment"
    SEPARATOR = "separator"
    GARBAGE = "garbage"


class HashType(Enum):
    """Common hash types found in credential dumps."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"
    BCRYPT = "bcrypt"
    NTLM = "ntlm"
    UNKNOWN = "unknown"


@dataclass
class CredentialEntry:
    """Normalized credential entry."""
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    password_hash: Optional[str] = None
    hash_type: Optional[str] = None
    salt: Optional[str] = None
    additional_fields: Optional[Dict[str, str]] = None
    
    # Metadata
    confidence: float = 0.0
    line_number: int = 0
    detected_format: str = ""
    source_line: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values and internal fields."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None and key != 'source_line':
                if key == 'additional_fields' and not value:
                    continue
                result[key] = value
        return result


class PatternLibrary:
    """Library of regex patterns for credential detection."""
    
    # Email pattern
    EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # Hash patterns by length and character set
    MD5 = re.compile(r'\b[a-fA-F0-9]{32}\b')
    SHA1 = re.compile(r'\b[a-fA-F0-9]{40}\b')
    SHA256 = re.compile(r'\b[a-fA-F0-9]{64}\b')
    SHA512 = re.compile(r'\b[a-fA-F0-9]{128}\b')
    BCRYPT = re.compile(r'\$2[ayb]\$\d{2}\$[./A-Za-z0-9]{53}')
    NTLM = re.compile(r'\b[a-fA-F0-9]{32}\b')  # Same as MD5, need context
    
    # Common delimiters
    DELIMITERS = [':', '|', ';', '\t', ',', ' - ', '--', '==']
    
    # Username patterns (alphanumeric, dots, underscores, hyphens)
    USERNAME = re.compile(r'^[a-zA-Z0-9._-]{3,32}$')
    
    # Common credential dump headers/footers
    NOISE_PATTERNS = [
        re.compile(r'^[\s\-=*#]+$'),  # Lines with only special chars
        re.compile(r'^(username|email|password|hash|user|pass|login)', re.IGNORECASE),
        re.compile(r'(database|dump|leak|breach|combo)', re.IGNORECASE),
    ]


class FeatureExtractor:
    """Extract features from text lines for classification."""
    
    @staticmethod
    def extract_features(line: str) -> Dict[str, Any]:
        """Extract features from a line of text."""
        features = {}
        
        # Basic statistics
        features['length'] = len(line)
        features['has_email'] = bool(PatternLibrary.EMAIL.search(line))
        features['has_md5'] = bool(PatternLibrary.MD5.search(line))
        features['has_sha1'] = bool(PatternLibrary.SHA1.search(line))
        features['has_sha256'] = bool(PatternLibrary.SHA256.search(line))
        
        # Character type ratios
        if len(line) > 0:
            features['alpha_ratio'] = sum(c.isalpha() for c in line) / len(line)
            features['digit_ratio'] = sum(c.isdigit() for c in line) / len(line)
            features['special_ratio'] = sum(not c.isalnum() and not c.isspace() for c in line) / len(line)
            features['whitespace_ratio'] = sum(c.isspace() for c in line) / len(line)
        else:
            features['alpha_ratio'] = 0.0
            features['digit_ratio'] = 0.0
            features['special_ratio'] = 0.0
            features['whitespace_ratio'] = 0.0
        
        # Delimiter detection
        features['delimiter'] = FeatureExtractor.detect_delimiter(line)
        features['field_count'] = len(line.split(features['delimiter'])) if features['delimiter'] else 1
        
        # Entropy (measure of randomness)
        features['entropy'] = FeatureExtractor.calculate_entropy(line)
        
        return features
    
    @staticmethod
    def detect_delimiter(line: str) -> Optional[str]:
        """Detect the most likely delimiter in a line."""
        delimiter_counts = {}
        for delim in PatternLibrary.DELIMITERS:
            count = line.count(delim)
            if count > 0:
                delimiter_counts[delim] = count
        
        if not delimiter_counts:
            return None
        
        # Return delimiter that appears most frequently
        return max(delimiter_counts.items(), key=lambda x: x[1])[0]
    
    @staticmethod
    def calculate_entropy(text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        import math
        entropy = 0.0
        text_len = len(text)
        for count in char_counts.values():
            probability = count / text_len
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy


class LineClassifier:
    """Classify lines as valid credentials or noise."""
    
    @staticmethod
    def classify(line: str, features: Dict[str, Any]) -> Tuple[LineType, float]:
        """
        Classify a line and return confidence score.
        
        Returns:
            Tuple of (LineType, confidence_score)
        """
        # Empty or very short lines
        if len(line.strip()) < 3:
            return LineType.GARBAGE, 1.0
        
        # Lines with only separators (check before noise patterns)
        if re.match(r'^[\s\-=*#]+$', line):
            return LineType.SEPARATOR, 0.9
        
        # Heuristic scoring for valid credential
        score = 0.0
        
        # Has email or username-like field
        if features['has_email']:
            score += 0.4
        elif features['alpha_ratio'] > 0.3 and features['alpha_ratio'] < 0.9:
            score += 0.2
        
        # Has hash
        if features['has_md5'] or features['has_sha1'] or features['has_sha256']:
            score += 0.3
        
        # Has delimiter
        if features['delimiter']:
            score += 0.2
        
        # Field count (2-5 fields typical for credentials)
        if 2 <= features['field_count'] <= 5:
            score += 0.1
        
        # Reasonable entropy (not too random, not too uniform)
        if 2.0 < features['entropy'] < 5.0:
            score += 0.1
        
        # Length check (typical credential lines are 20-200 chars)
        if 20 <= features['length'] <= 200:
            score += 0.1
        
        # Classify based on score
        if score >= 0.6:
            return LineType.VALID_CREDENTIAL, min(score, 1.0)
        
        # Check for noise patterns (after credential check)
        for pattern in PatternLibrary.NOISE_PATTERNS:
            if pattern.search(line):
                return LineType.HEADER, 0.8
        
        return LineType.GARBAGE, 1.0 - score
    

class FieldExtractor:
    """Extract and identify fields from credential lines."""
    
    @staticmethod
    def extract_fields(line: str, delimiter: Optional[str]) -> List[str]:
        """Split line into fields using detected delimiter."""
        if not delimiter:
            # Try to split by whitespace if no delimiter detected
            fields = line.split()
            if len(fields) == 1:
                # Single field, return as-is
                return [line.strip()]
            return [f.strip() for f in fields]
        
        fields = line.split(delimiter)
        return [f.strip() for f in fields if f.strip()]
    
    @staticmethod
    def identify_hash_type(hash_str: str) -> HashType:
        """Identify the type of hash."""
        hash_str = hash_str.strip()
        
        if PatternLibrary.BCRYPT.match(hash_str):
            return HashType.BCRYPT
        elif PatternLibrary.SHA512.match(hash_str):
            return HashType.SHA512
        elif PatternLibrary.SHA256.match(hash_str):
            return HashType.SHA256
        elif PatternLibrary.SHA1.match(hash_str):
            return HashType.SHA1
        elif PatternLibrary.MD5.match(hash_str):
            # Could be MD5 or NTLM, default to MD5
            return HashType.MD5
        else:
            return HashType.UNKNOWN
    
    @staticmethod
    def parse_credential_line(line: str, delimiter: Optional[str]) -> CredentialEntry:
        """Parse a line into a CredentialEntry."""
        fields = FieldExtractor.extract_fields(line, delimiter)
        entry = CredentialEntry()
        
        if not fields:
            return entry
        
        # Identify each field
        email_found = False
        hash_found = False
        
        for field in fields:
            field = field.strip()
            if not field:
                continue
            
            # Check for email
            if not email_found and PatternLibrary.EMAIL.match(field):
                entry.email = field
                email_found = True
                continue
            
            # Check for hash
            hash_type = FieldExtractor.identify_hash_type(field)
            if not hash_found and hash_type != HashType.UNKNOWN:
                entry.password_hash = field
                entry.hash_type = hash_type.value
                hash_found = True
                continue
            
            # Check for username (if no email yet)
            if not entry.username and not email_found and PatternLibrary.USERNAME.match(field):
                entry.username = field
                continue
            
            # Otherwise, assume it's a password (if we don't have one yet)
            if not entry.password and not hash_found:
                # Plain text password
                entry.password = field
        
        return entry


class MLNormalizer:
    """Main ML-based normalizer for credential dumps."""
    
    def __init__(self, use_language_model: bool = False):
        """
        Initialize the normalizer.
        
        Args:
            use_language_model: Whether to use language model for ambiguous cases
        """
        self.use_lm = use_language_model
        self.feature_extractor = FeatureExtractor()
        self.classifier = LineClassifier()
        self.field_extractor = FieldExtractor()
        
        if use_language_model:
            logger.warning("Language model support not yet implemented. Falling back to classical ML.")
    
    def normalize_line(self, line: str, line_number: int) -> Optional[CredentialEntry]:
        """
        Normalize a single line from a credential dump.
        
        Args:
            line: The line to parse
            line_number: Line number in source file
            
        Returns:
            CredentialEntry if valid credential found, None otherwise
        """
        # Clean the line
        line = self._clean_line(line)
        
        if not line:
            return None
        
        # Extract features
        features = self.feature_extractor.extract_features(line)
        
        # Classify line
        line_type, confidence = self.classifier.classify(line, features)
        
        if line_type != LineType.VALID_CREDENTIAL:
            return None
        
        # Extract fields
        entry = self.field_extractor.parse_credential_line(line, features['delimiter'])
        
        # Set metadata
        entry.confidence = confidence
        entry.line_number = line_number
        entry.source_line = line
        entry.detected_format = self._detect_format(entry, features)
        
        # Validate entry has at least some useful data
        if not any([entry.email, entry.username, entry.password, entry.password_hash]):
            return None
        
        return entry
    
    def normalize_file(self, input_path: str, output_path: str, 
                       min_confidence: float = 0.5) -> Dict[str, int]:
        """
        Normalize an entire credential dump file.
        
        Args:
            input_path: Path to input file
            output_path: Path to output JSONL file
            min_confidence: Minimum confidence threshold
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_lines': 0,
            'valid_credentials': 0,
            'filtered_low_confidence': 0,
            'errors': 0
        }
        
        try:
            with open(input_path, 'r', encoding='utf-8', errors='replace') as infile, \
                 open(output_path, 'w', encoding='utf-8') as outfile:
                
                for line_num, line in enumerate(infile, start=1):
                    stats['total_lines'] += 1
                    
                    try:
                        entry = self.normalize_line(line, line_num)
                        
                        if entry and entry.confidence >= min_confidence:
                            stats['valid_credentials'] += 1
                            json.dump(entry.to_dict(), outfile)
                            outfile.write('\n')
                        elif entry:
                            stats['filtered_low_confidence'] += 1
                    
                    except Exception as e:
                        stats['errors'] += 1
                        logger.debug(f"Error processing line {line_num}: {e}")
        
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            raise
        
        return stats
    
    @staticmethod
    def _clean_line(line: str) -> str:
        """Clean and normalize a line."""
        # Strip whitespace
        line = line.strip()
        
        # Remove null bytes
        line = line.replace('\x00', '')
        
        # Normalize excessive whitespace
        line = re.sub(r'\s+', ' ', line)
        
        return line
    
    @staticmethod
    def _detect_format(entry: CredentialEntry, features: Dict[str, Any]) -> str:
        """Detect the format of the credential entry."""
        parts = []
        
        if entry.email:
            parts.append('email')
        if entry.username:
            parts.append('username')
        if entry.password:
            parts.append('password')
        if entry.password_hash:
            parts.append('hash')
        
        delimiter = features.get('delimiter', ':')
        return delimiter.join(parts) if parts else 'unknown'


def main():
    """Example usage."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python ml_normalizer.py <input_file> <output_file> [min_confidence]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    min_confidence = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    
    normalizer = MLNormalizer()
    
    logger.info(f"Processing {input_file}...")
    stats = normalizer.normalize_file(input_file, output_file, min_confidence)
    
    logger.info("Processing complete!")
    logger.info(f"Total lines: {stats['total_lines']}")
    logger.info(f"Valid credentials: {stats['valid_credentials']}")
    logger.info(f"Filtered (low confidence): {stats['filtered_low_confidence']}")
    logger.info(f"Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
