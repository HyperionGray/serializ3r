"""
Test suite for ML-based credential normalizer.
"""

import unittest
import json
import os
import tempfile
from ml_normalizer import (
    MLNormalizer, CredentialEntry, FeatureExtractor, 
    LineClassifier, FieldExtractor, PatternLibrary,
    LineType, HashType
)


class TestPatternLibrary(unittest.TestCase):
    """Test pattern matching."""
    
    def test_email_pattern(self):
        """Test email pattern matching."""
        self.assertTrue(PatternLibrary.EMAIL.search("user@example.com"))
        self.assertTrue(PatternLibrary.EMAIL.search("test.user+tag@example.co.uk"))
        self.assertFalse(PatternLibrary.EMAIL.search("not-an-email"))
        self.assertFalse(PatternLibrary.EMAIL.search("@example.com"))
    
    def test_hash_patterns(self):
        """Test hash pattern matching."""
        # MD5
        self.assertTrue(PatternLibrary.MD5.match("5f4dcc3b5aa765d61d8327deb882cf99"))
        self.assertFalse(PatternLibrary.MD5.match("not-a-hash"))
        
        # SHA1
        self.assertTrue(PatternLibrary.SHA1.match("5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"))
        
        # SHA256
        self.assertTrue(PatternLibrary.SHA256.match(
            "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
        ))
        
        # bcrypt
        self.assertTrue(PatternLibrary.BCRYPT.match(
            "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"
        ))


class TestFeatureExtractor(unittest.TestCase):
    """Test feature extraction."""
    
    def test_basic_features(self):
        """Test basic feature extraction."""
        line = "user@example.com:password123"
        features = FeatureExtractor.extract_features(line)
        
        self.assertIn('length', features)
        self.assertIn('has_email', features)
        self.assertIn('delimiter', features)
        self.assertEqual(features['length'], len(line))
        self.assertTrue(features['has_email'])
        self.assertEqual(features['delimiter'], ':')
    
    def test_delimiter_detection(self):
        """Test delimiter detection."""
        self.assertEqual(FeatureExtractor.detect_delimiter("a:b:c"), ':')
        self.assertEqual(FeatureExtractor.detect_delimiter("a|b|c"), '|')
        self.assertEqual(FeatureExtractor.detect_delimiter("a\tb\tc"), '\t')
        self.assertIsNone(FeatureExtractor.detect_delimiter("abc"))
    
    def test_entropy_calculation(self):
        """Test entropy calculation."""
        # Uniform string (low entropy)
        low_entropy = FeatureExtractor.calculate_entropy("aaaaaaaaaa")
        
        # Random-looking string (higher entropy)
        high_entropy = FeatureExtractor.calculate_entropy("a1b2c3d4e5")
        
        self.assertGreater(high_entropy, low_entropy)


class TestLineClassifier(unittest.TestCase):
    """Test line classification."""
    
    def test_valid_credential_classification(self):
        """Test classification of valid credential lines."""
        line = "user@example.com:password123"
        features = FeatureExtractor.extract_features(line)
        line_type, confidence = LineClassifier.classify(line, features)
        
        self.assertEqual(line_type, LineType.VALID_CREDENTIAL)
        self.assertGreater(confidence, 0.5)
    
    def test_garbage_classification(self):
        """Test classification of garbage lines."""
        line = "@@@@@@@@@@@@"
        features = FeatureExtractor.extract_features(line)
        line_type, confidence = LineClassifier.classify(line, features)
        
        self.assertNotEqual(line_type, LineType.VALID_CREDENTIAL)
    
    def test_separator_classification(self):
        """Test classification of separator lines."""
        line = "================================"
        features = FeatureExtractor.extract_features(line)
        line_type, confidence = LineClassifier.classify(line, features)
        
        self.assertEqual(line_type, LineType.SEPARATOR)


class TestFieldExtractor(unittest.TestCase):
    """Test field extraction."""
    
    def test_field_extraction(self):
        """Test extracting fields from a line."""
        fields = FieldExtractor.extract_fields("a:b:c", ':')
        self.assertEqual(fields, ['a', 'b', 'c'])
        
        fields = FieldExtractor.extract_fields("a|b|c", '|')
        self.assertEqual(fields, ['a', 'b', 'c'])
    
    def test_hash_type_identification(self):
        """Test hash type identification."""
        # MD5
        hash_type = FieldExtractor.identify_hash_type("5f4dcc3b5aa765d61d8327deb882cf99")
        self.assertEqual(hash_type, HashType.MD5)
        
        # SHA1
        hash_type = FieldExtractor.identify_hash_type("5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8")
        self.assertEqual(hash_type, HashType.SHA1)
        
        # SHA256
        hash_type = FieldExtractor.identify_hash_type(
            "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
        )
        self.assertEqual(hash_type, HashType.SHA256)
        
        # bcrypt
        hash_type = FieldExtractor.identify_hash_type(
            "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"
        )
        self.assertEqual(hash_type, HashType.BCRYPT)
    
    def test_credential_parsing(self):
        """Test parsing credential lines."""
        # Email:password format
        entry = FieldExtractor.parse_credential_line("user@example.com:password123", ':')
        self.assertEqual(entry.email, "user@example.com")
        self.assertEqual(entry.password, "password123")
        
        # Email:hash format
        entry = FieldExtractor.parse_credential_line(
            "user@example.com:5f4dcc3b5aa765d61d8327deb882cf99", ':'
        )
        self.assertEqual(entry.email, "user@example.com")
        self.assertEqual(entry.password_hash, "5f4dcc3b5aa765d61d8327deb882cf99")
        self.assertEqual(entry.hash_type, "md5")
        
        # Username:password format
        entry = FieldExtractor.parse_credential_line("john_doe:secretpass", ':')
        self.assertEqual(entry.username, "john_doe")
        self.assertEqual(entry.password, "secretpass")


class TestCredentialEntry(unittest.TestCase):
    """Test CredentialEntry dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        entry = CredentialEntry(
            email="test@example.com",
            password="testpass",
            confidence=0.95,
            line_number=1,
            detected_format="email:password"
        )
        
        result = entry.to_dict()
        self.assertEqual(result['email'], "test@example.com")
        self.assertEqual(result['password'], "testpass")
        self.assertNotIn('source_line', result)  # Should be excluded
        self.assertNotIn('additional_fields', result)  # Should be excluded if None/empty


class TestMLNormalizer(unittest.TestCase):
    """Test the main MLNormalizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = MLNormalizer()
    
    def test_normalize_simple_line(self):
        """Test normalizing a simple credential line."""
        entry = self.normalizer.normalize_line("user@example.com:password123", 1)
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.email, "user@example.com")
        self.assertEqual(entry.password, "password123")
        self.assertEqual(entry.line_number, 1)
        self.assertGreater(entry.confidence, 0.0)
    
    def test_normalize_hash_line(self):
        """Test normalizing a line with a hash."""
        entry = self.normalizer.normalize_line(
            "user@example.com:5f4dcc3b5aa765d61d8327deb882cf99", 1
        )
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.email, "user@example.com")
        self.assertEqual(entry.password_hash, "5f4dcc3b5aa765d61d8327deb882cf99")
        self.assertEqual(entry.hash_type, "md5")
    
    def test_normalize_garbage_line(self):
        """Test that garbage lines return None."""
        entry = self.normalizer.normalize_line("@@@@@@@@@@@", 1)
        self.assertIsNone(entry)
        
        entry = self.normalizer.normalize_line("", 1)
        self.assertIsNone(entry)
    
    def test_normalize_file(self):
        """Test normalizing an entire file."""
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("user1@example.com:password1\n")
            f.write("user2@example.com:password2\n")
            f.write("garbage line\n")
            f.write("user3@example.com:5f4dcc3b5aa765d61d8327deb882cf99\n")
            input_file = f.name
        
        # Create temporary output file
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl').name
        
        try:
            # Process file
            stats = self.normalizer.normalize_file(input_file, output_file, min_confidence=0.5)
            
            # Check stats
            self.assertEqual(stats['total_lines'], 4)
            self.assertGreater(stats['valid_credentials'], 0)
            
            # Check output file
            with open(output_file, 'r') as f:
                lines = f.readlines()
                self.assertGreater(len(lines), 0)
                
                # Verify each line is valid JSON
                for line in lines:
                    data = json.loads(line)
                    self.assertIn('email', data)
                    self.assertIn('confidence', data)
        
        finally:
            # Clean up
            os.unlink(input_file)
            os.unlink(output_file)
    
    def test_clean_line(self):
        """Test line cleaning."""
        cleaned = MLNormalizer._clean_line("  test  \n")
        self.assertEqual(cleaned, "test")
        
        cleaned = MLNormalizer._clean_line("test\x00string")
        self.assertEqual(cleaned, "teststring")
        
        cleaned = MLNormalizer._clean_line("test   multiple   spaces")
        self.assertEqual(cleaned, "test multiple spaces")


class TestIntegration(unittest.TestCase):
    """Integration tests with test data file."""
    
    def test_process_test_data(self):
        """Test processing the test data file."""
        normalizer = MLNormalizer()
        
        # Check if test data file exists
        test_data_path = os.path.join(os.path.dirname(__file__), 'test_data.txt')
        if not os.path.exists(test_data_path):
            self.skipTest("test_data.txt not found")
        
        # Create temporary output file
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jsonl').name
        
        try:
            # Process the test data
            stats = normalizer.normalize_file(test_data_path, output_file, min_confidence=0.5)
            
            # Check that we processed lines
            self.assertGreater(stats['total_lines'], 0)
            self.assertGreater(stats['valid_credentials'], 0)
            
            # Verify output
            with open(output_file, 'r') as f:
                entries = [json.loads(line) for line in f]
                
                # Should have extracted multiple credentials
                self.assertGreater(len(entries), 10)
                
                # Check some entries have emails
                emails = [e.get('email') for e in entries if e.get('email')]
                self.assertGreater(len(emails), 5)
                
                # Check some entries have hashes
                hashes = [e.get('password_hash') for e in entries if e.get('password_hash')]
                self.assertGreater(len(hashes), 3)
        
        finally:
            # Clean up
            os.unlink(output_file)


if __name__ == '__main__':
    unittest.main()
