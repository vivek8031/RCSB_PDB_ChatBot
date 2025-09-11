#!/usr/bin/env python3
"""
Test Cases Based on User Feedback
Comprehensive test scenarios to validate chatbot improvements
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"

class FeedbackCategory(Enum):
    BIOCURATOR_LANGUAGE = "biocurator_language"
    REDUNDANCY = "redundancy"
    REFERENCES = "references"
    DEPOSITOR_FOCUS = "depositor_focus"
    COMPLETENESS = "completeness"
    INTERNAL_INSTRUCTIONS = "internal_instructions"

@dataclass
class TestCase:
    """Represents a single test case based on user feedback"""
    id: str
    question: str
    category: FeedbackCategory
    severity: Severity
    user_source: str  # Who reported this issue (Brian, Chenghua, etc.)
    description: str
    forbidden_content: List[str]  # Content that should NOT appear
    required_content: List[str]   # Content that SHOULD appear
    max_response_length: int = None  # For verbosity testing
    
class UserFeedbackTestSuite:
    """Complete test suite based on user feedback"""
    
    def __init__(self):
        self.test_cases = self._initialize_test_cases()
    
    def _initialize_test_cases(self) -> List[TestCase]:
        """Initialize all test cases based on user feedback"""
        return [
            # Brian's Feedback - Biocurator Language Issues
            TestCase(
                id="BRIAN_001",
                question="Cannot Find Deposition Session When Logged In with ORCID",
                category=FeedbackCategory.BIOCURATOR_LANGUAGE,
                severity=Severity.CRITICAL,
                user_source="Brian",
                description="Should not mention Ezra or biocurator-specific instructions",
                forbidden_content=[
                    "Ezra", "biocurator", "annotator", "allow submit",
                    "RT instructions", "triage", "(for example, Ezra)"
                ],
                required_content=[
                    "support staff", "support team", "RCSB PDB staff"
                ]
            ),
            
            # Brian's Feedback - Verbosity Issues  
            TestCase(
                id="BRIAN_002", 
                question="What file formats are accepted for protein structure deposition?",
                category=FeedbackCategory.REDUNDANCY,
                severity=Severity.HIGH,
                user_source="Brian",
                description="Should not have redundant Summary or Key Points sections",
                forbidden_content=[
                    "## Summary", "### Summary", "**Summary**:",
                    "## Key Points:", "### Key Points:", "**Key Points**:"
                ],
                required_content=[
                    "PDBx/mmCIF", "PDB format", "structure factor"
                ],
                max_response_length=500  # Should be concise
            ),
            
            # Chenghua's Feedback - Internal References
            TestCase(
                id="CHENGHUA_001",
                question="I cannot find my deposition session when logged in with ORCID",
                category=FeedbackCategory.BIOCURATOR_LANGUAGE, 
                severity=Severity.HIGH,
                user_source="Chenghua",
                description="Should not mention internal staff names like Ezra",
                forbidden_content=[
                    "Ezra", "contact Ezra", "assistance can be provided to link"
                ],
                required_content=[
                    "support staff", "contact support", "RCSB PDB support"
                ]
            ),
            
            TestCase(
                id="CHENGHUA_002",
                question="Whom to contact for deposition problems", 
                category=FeedbackCategory.INTERNAL_INSTRUCTIONS,
                severity=Severity.MEDIUM,
                user_source="Chenghua",
                description="Should not reference internal triage sections",
                forbidden_content=[
                    "D_12XXXXXXXX", "D_13XXXXXXXX", "triage QA",
                    "entries with Deposition IDs starting with D_12"
                ],
                required_content=[
                    "support team", "deposition support", "contact information"
                ]
            ),
            
            # Irina's Feedback - Reference Issues
            TestCase(
                id="IRINA_001",
                question="What is the obsolete policy in the PDB?",
                category=FeedbackCategory.REFERENCES,
                severity=Severity.CRITICAL,
                user_source="Irina", 
                description="Should not show raw reference IDs and should include complete policy info",
                forbidden_content=[
                    "[ID:0]", "[ID:1]", "References: [ID:", 
                    "Available reference IDs:"
                ],
                required_content=[
                    "no associated publication", "entry author obsoletes",
                    "structurally incorrect"
                ]
            ),
            
            TestCase(
                id="IRINA_002",
                question="How do I update my structure after initial deposition?",
                category=FeedbackCategory.REFERENCES,
                severity=Severity.MEDIUM, 
                user_source="Irina",
                description="Should format references cleanly without raw IDs",
                forbidden_content=[
                    "References: [ID:0]", "[ID:1] [ID:2]", "Available reference IDs"
                ],
                required_content=[
                    "According to", "documentation", "policy"
                ]
            ),
            
            # Gregg's Feedback - Complex Scenarios and Internal Instructions
            TestCase(
                id="GREGG_001",
                question="How do I deposit 75 structures of the same protein with different fragments? I do not want to input the same experimental information 75 times.",
                category=FeedbackCategory.INTERNAL_INSTRUCTIONS,
                severity=Severity.CRITICAL,
                user_source="Gregg",
                description="Should not include internal notes about RT or disclosure restrictions",
                forbidden_content=[
                    "Instructions for the Group Deposition system should not be disclosed over RT",
                    "Notes for annotators", "should not be disclosed",
                    "RT or other publicly visible means"
                ],
                required_content=[
                    "group deposition", "batch submission", "experimental information"
                ]
            ),
            
            TestCase(
                id="GREGG_002", 
                question="OneDep says that my ligand is not in the PDB but I know that it is there",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.HIGH,
                user_source="Gregg",
                description="Should provide instructional guidance, not just policy information",
                forbidden_content=[
                    "policy states", "according to policy", "theoretical"
                ],
                required_content=[
                    "upload", "diagram", "contact support", "provide"
                ]
            ),
            
            TestCase(
                id="GREGG_003",
                question="What should I do when OneDep validation fails?",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.MEDIUM,
                user_source="Gregg", 
                description="Should end with clear guidance to contact human support",
                forbidden_content=[
                    "annotators", "internal process", "biocurator review"
                ],
                required_content=[
                    "Contact", "support", "guidance", "help"
                ]
            ),
            
            # Sutapa's Feedback - Practical Depositor Issues
            TestCase(
                id="SUTAPA_001",
                question="All the items in my on-going deposition is flagged in green, yet the submit deposition button is not showing up. Please help to complete my deposition",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.CRITICAL,
                user_source="Sutapa",
                description="Should recommend contacting annotator early, not list many possibilities first",
                forbidden_content=[
                    "one common cause is", "you have not yet downloaded",
                    "many possibilities", "validation tab", "accept terms"
                ],
                required_content=[
                    "contact support", "annotator", "look into this", "assistance"
                ]
            ),
            
            TestCase(
                id="SUTAPA_002",
                question="The sequences for all chains in this deposition are not deposited in Genbank or Uniprot, as this is a Fab fragment that was generated by phage display. Unfortunately the submission GUI wants me to provide a link to one of these two databases for the sequence, and I can't clear it in order to finalize the submission. Please help.",
                category=FeedbackCategory.DEPOSITOR_FOCUS, 
                severity=Severity.HIGH,
                user_source="Sutapa",
                description="Should lead with the correct action (communication page), not bury it",
                forbidden_content=[
                    "Recommended Action:", "fifth", "last bullet point"
                ],
                required_content=[
                    "communication page", "request assistance", "phage display", 
                    "not present in sequence databases", "self-referenced"
                ]
            ),
            
            # Additional Test Cases for Edge Cases
            TestCase(
                id="EDGE_001",
                question="How do I reset the deposition interface?",
                category=FeedbackCategory.INTERNAL_INSTRUCTIONS,
                severity=Severity.MEDIUM,
                user_source="Irina",
                description="Should not include biocurator-specific reset instructions",
                forbidden_content=[
                    "biocurator", "internal process", "annotator access"
                ],
                required_content=[
                    "deposition interface", "reset", "upload"
                ]
            ),
            
            TestCase(
                id="EDGE_002", 
                question="What validation checks are performed during deposition?",
                category=FeedbackCategory.REDUNDANCY,
                severity=Severity.MEDIUM,
                user_source="General",
                description="Should be concise without redundant summaries",
                forbidden_content=[
                    "## Summary", "### Key Points:", "**Summary**"
                ],
                required_content=[
                    "validation", "checks", "geometry", "structure"
                ]
            ),
            
            # New Test Cases for Solution Prioritization and Instructional Focus
            TestCase(
                id="PRIORITIZATION_001",
                question="OneDep says that my ligand is not in the PDB but I know that it is there",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.HIGH,
                user_source="Gregg",
                description="Should prioritize instructional guidance over theoretical policy",
                forbidden_content=[
                    "policy states", "theoretical", "according to policy",
                    "many possibilities", "several options", "could be"
                ],
                required_content=[
                    "upload", "diagram", "provide", "attach", "submit"
                ],
                max_response_length=400  # Should be concise and direct
            ),
            
            TestCase(
                id="PRIORITIZATION_002",
                question="All items in my deposition are flagged green, yet the submit button is not showing up",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.CRITICAL,
                user_source="Sutapa",
                description="Should prioritize contacting support early, not bury in possibilities",
                forbidden_content=[
                    "one common cause is", "many possibilities", "several reasons",
                    "could be due to", "might be because", "there are several"
                ],
                required_content=[
                    "contact support", "assistance", "support staff"
                ],
                max_response_length=300  # Should be direct
            ),
            
            TestCase(
                id="INSTRUCTIONAL_001", 
                question="How do I fix validation errors in my structure?",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.HIGH,
                user_source="General",
                description="Should provide step-by-step instructions not theoretical explanations",
                forbidden_content=[
                    "validation is important", "policy requires", "the system checks",
                    "this is because", "validation ensures"
                ],
                required_content=[
                    "1.", "2.", "first", "then", "next", "step"
                ]
            ),
            
            TestCase(
                id="INSTRUCTIONAL_002",
                question="The sequences are not in GenBank or UniProt, as this is a Fab fragment from phage display",
                category=FeedbackCategory.DEPOSITOR_FOCUS,
                severity=Severity.CRITICAL,
                user_source="Sutapa",
                description="Should lead with correct action, not bury as last option",
                forbidden_content=[
                    "Recommended Action:", "fifth", "last bullet point", "final option",
                    "alternatively", "you could also", "another possibility"
                ],
                required_content=[
                    "communication page", "request assistance", "phage display",
                    "self-referenced", "not present in sequence databases"
                ]
            )
        ]
    
    def get_tests_by_category(self, category: FeedbackCategory) -> List[TestCase]:
        """Get all test cases for a specific category"""
        return [test for test in self.test_cases if test.category == category]
    
    def get_tests_by_severity(self, severity: Severity) -> List[TestCase]:
        """Get all test cases for a specific severity level"""
        return [test for test in self.test_cases if test.severity == severity]
    
    def get_tests_by_user(self, user_source: str) -> List[TestCase]:
        """Get all test cases from a specific user's feedback"""
        return [test for test in self.test_cases if test.user_source.lower() == user_source.lower()]
    
    def get_critical_tests(self) -> List[TestCase]:
        """Get all critical severity test cases"""
        return self.get_tests_by_severity(Severity.CRITICAL)
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the test suite"""
        total_tests = len(self.test_cases)
        by_category = {}
        by_severity = {}
        by_user = {}
        
        for test in self.test_cases:
            # Count by category
            cat_name = test.category.value
            by_category[cat_name] = by_category.get(cat_name, 0) + 1
            
            # Count by severity  
            sev_name = test.severity.value
            by_severity[sev_name] = by_severity.get(sev_name, 0) + 1
            
            # Count by user
            user = test.user_source
            by_user[user] = by_user.get(user, 0) + 1
        
        return {
            "total_tests": total_tests,
            "by_category": by_category,
            "by_severity": by_severity, 
            "by_user": by_user
        }

# Example usage
if __name__ == "__main__":
    test_suite = UserFeedbackTestSuite()
    
    print(f"Total test cases: {len(test_suite.test_cases)}")
    print("\nTest Summary:")
    summary = test_suite.get_test_summary()
    
    print(f"By Category: {summary['by_category']}")
    print(f"By Severity: {summary['by_severity']}")
    print(f"By User: {summary['by_user']}")
    
    print("\nCritical Tests:")
    for test in test_suite.get_critical_tests():
        print(f"- {test.id}: {test.description}")