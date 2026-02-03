"""
Clean essay evaluator using only:
1. nltk for text processing
2. scikit-learn for TF-IDF & cosine similarity
3. language-tool-python for grammar
"""

import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import language_tool_python

# Try to import sklearn with fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not installed. Cohesion scoring will be limited.")

# Download required NLTK data with error handling
def download_nltk_data():
    """Download required NLTK data if not present"""
    try:
        # Check and download punkt tokenizer
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            print("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
        
        # Check and download stopwords
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            print("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True)
            
    except Exception as e:
        print(f"Warning: NLTK data download failed: {e}")
        return False
    
    return True

# Initialize NLTK data
NLTK_READY = download_nltk_data()

class EssayEvaluator:
    """
    Evaluates essays based on:
    1. Topic Relevance (30%) - Title vs Essay content
    2. Cohesion (30%) - Sentence flow using TF-IDF & cosine similarity
    3. Grammar Score (25%) - Using language_tool_python
    4. Structure & Length (15%) - Word count and paragraph structure
    """
    
    def __init__(self, competition_topic, min_words=500, max_words=2000):
        self.competition_topic = competition_topic
        self.min_words = min_words
        self.max_words = max_words
        
        # Initialize stopwords
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            self.stop_words = set(['a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
        
        # Initialize language tool
        try:
            self.tool = language_tool_python.LanguageTool('en-US')
        except Exception as e:
            print(f"Warning: LanguageTool initialization failed: {e}")
            self.tool = None
    
    def evaluate(self, essay_title, essay_content):
        """
        Main evaluation function that returns all scores
        Returns: dict with all scores (0-100 scale)
        """
        # Calculate individual scores with error handling
        try:
            topic_score = self._calculate_topic_relevance(essay_title, essay_content)
        except Exception as e:
            print(f"Topic relevance calculation error: {e}")
            topic_score = 50.0
        
        try:
            cohesion_score = self._calculate_cohesion(essay_content)
        except Exception as e:
            print(f"Cohesion calculation error: {e}")
            cohesion_score = 50.0
        
        try:
            grammar_score = self._calculate_grammar_score(essay_content)
        except Exception as e:
            print(f"Grammar calculation error: {e}")
            grammar_score = 50.0
        
        try:
            structure_score = self._calculate_structure_score(essay_content)
        except Exception as e:
            print(f"Structure calculation error: {e}")
            structure_score = 50.0
        
        # Calculate weighted total (weights as specified)
        total_score = (
            topic_score * 0.30 +
            cohesion_score * 0.30 +
            grammar_score * 0.25 +
            structure_score * 0.15
        )
        
        # Convert numpy floats to Python floats
        scores = {
            'topic_score': float(round(topic_score, 2)),
            'cohesion_score': float(round(cohesion_score, 2)),
            'grammar_score': float(round(grammar_score, 2)),
            'structure_score': float(round(structure_score, 2)),
            'total_score': float(round(total_score, 2))
        }
        
        return scores
    
    def _calculate_topic_relevance(self, title, content):
        """Calculate relevance between title/topic and essay content (0-100)"""
        if not content.strip() or not title.strip():
            return 50.0
        
        try:
            # Convert to lowercase for case-insensitive matching
            topic_lower = self.competition_topic.lower()
            title_lower = title.lower()
            content_lower = content.lower()
            
            # Combine topic and title for keyword extraction
            search_text = f"{topic_lower} {title_lower}"
            
            # Extract keywords (remove stopwords and short words)
            if NLTK_READY:
                search_words = word_tokenize(search_text)
                content_words = word_tokenize(content_lower)
            else:
                search_words = search_text.split()
                content_words = content_lower.split()
            
            # Get meaningful keywords (words > 3 chars, not stopwords)
            keywords = []
            for word in search_words:
                if (word.isalnum() and 
                    len(word) > 3 and 
                    word.lower() not in self.stop_words):
                    keywords.append(word.lower())
            
            # Remove duplicates
            keywords = list(set(keywords))
            
            if not keywords:
                return 50.0  # No meaningful keywords found
            
            # Calculate keyword presence in content
            matches = 0
            for keyword in keywords:
                # Check if keyword appears in content
                if keyword in content_lower:
                    matches += 1
                # Also check for partial matches (for compound words)
                elif len(keyword) > 5:
                    # Check if part of the keyword appears
                    for word in content_words:
                        if len(word) > 3 and (keyword in word or word in keyword):
                            matches += 0.5
                            break
            
            # Calculate percentage score
            if matches > 0:
                score = (matches / len(keywords)) * 100
                # Add base score to ensure reasonable minimum
                score = max(30, min(score, 100))
                return score
            else:
                return 30.0  # Minimum score for any essay
            
        except Exception as e:
            print(f"Topic relevance error: {e}")
            return 50.0  # Default score on error
    
    def _calculate_cohesion(self, content):
        """Calculate cohesion using TF-IDF and cosine similarity (0-100)"""
        if not SKLEARN_AVAILABLE:
            # Fallback cohesion score without sklearn
            return self._fallback_cohesion_score(content)
        
        try:
            if NLTK_READY:
                sentences = sent_tokenize(content)
            else:
                # Simple sentence splitting fallback
                sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
            
            if len(sentences) < 2:
                return 50.0  # Not enough sentences for cohesion analysis
            
            # Calculate TF-IDF vectors
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Calculate cosine similarity between consecutive sentences
            similarities = []
            for i in range(len(sentences) - 1):
                sim = cosine_similarity(tfidf_matrix[i:i+1], tfidf_matrix[i+1:i+2])[0][0]
                similarities.append(sim)
            
            # Average similarity (0-1 scale) converted to 0-100
            if similarities:
                avg_similarity = sum(similarities) / len(similarities)
                # Scale and adjust for realistic scores
                # Good essays have 0.2-0.4 similarity, convert to 70-90 range
                if avg_similarity < 0.1:
                    score = 50.0
                elif avg_similarity < 0.2:
                    score = 60.0 + (avg_similarity * 100)
                elif avg_similarity < 0.3:
                    score = 70.0 + ((avg_similarity - 0.2) * 100)
                elif avg_similarity < 0.4:
                    score = 80.0 + ((avg_similarity - 0.3) * 100)
                else:
                    score = 90.0 + min((avg_similarity - 0.4) * 50, 10.0)
                
                return min(score, 100.0)
            else:
                return 50.0
            
        except Exception as e:
            print(f"Cohesion calculation error: {e}")
            return self._fallback_cohesion_score(content)
    
    def _fallback_cohesion_score(self, content):
        """Fallback cohesion calculation when sklearn is not available"""
        # Simple cohesion based on paragraph structure and transition words
        score = 50.0
        
        # Check paragraph count
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 3:
            score += 20
        
        # Check for transition words
        transition_words = [
            'however', 'therefore', 'moreover', 'furthermore', 
            'consequently', 'similarly', 'additionally', 'thus',
            'in addition', 'on the other hand', 'for example',
            'as a result', 'in conclusion', 'nevertheless'
        ]
        
        transition_count = 0
        content_lower = content.lower()
        for word in transition_words:
            if word in content_lower:
                transition_count += 1
        
        if transition_count >= 3:
            score += 15
        elif transition_count >= 2:
            score += 10
        elif transition_count >= 1:
            score += 5
        
        return min(score, 100.0)
    
    def _calculate_grammar_score(self, content):
        """Calculate grammar score using language_tool_python (0-100)"""
        if not content.strip():
            return 0.0
        
        if not self.tool:
            return 75.0  # Default grammar score if tool not available
        
        try:
            # Check for grammar errors
            matches = self.tool.check(content)
            
            # Count words
            if NLTK_READY:
                words = word_tokenize(content)
            else:
                words = content.split()
            
            if not words:
                return 100.0
            
            # Calculate error rate
            error_rate = len(matches) / len(words)
            
            # Convert to score: lower error rate = higher score
            # Scale: 0 errors = 100, 0.01 error rate (1 error per 100 words) = 95, etc.
            grammar_score = max(0, 100 - (error_rate * 1000))
            
            return min(grammar_score, 100.0)
            
        except Exception as e:
            print(f"Grammar check error: {e}")
            return 50.0
    
    def _calculate_structure_score(self, content):
        """Calculate structure score based on length and paragraphs (0-100)"""
        if not content.strip():
            return 0.0
        
        try:
            words = content.split()
            word_count = len(words)
            
            # Calculate length score (70% of structure score)
            length_score = 0
            if self.min_words <= word_count <= self.max_words:
                length_score = 70  # Perfect length
            elif word_count < self.min_words:
                # Linear scale for short essays
                ratio = word_count / self.min_words
                length_score = ratio * 70
            else:
                # Penalize for being too long, but not too harsh
                if word_count <= self.max_words * 1.5:
                    ratio = self.max_words / word_count
                    length_score = ratio * 70
                else:
                    length_score = 30  # Minimum for very long essays
            
            # Calculate paragraph score (30% of structure score)
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            para_score = 0
            if len(paragraphs) >= 5:
                para_score = 30  # Excellent structure
            elif len(paragraphs) >= 4:
                para_score = 25
            elif len(paragraphs) >= 3:
                para_score = 20
            elif len(paragraphs) >= 2:
                para_score = 15
            elif len(paragraphs) >= 1:
                para_score = 10
            
            total_structure_score = length_score + para_score
            return min(total_structure_score, 100.0)
            
        except Exception as e:
            print(f"Structure calculation error: {e}")
            return 50.0