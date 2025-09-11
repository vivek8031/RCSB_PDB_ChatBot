#!/usr/bin/env python3
"""
CrewAI Evaluation Agents for RCSB PDB ChatBot Testing
Specialized agents to evaluate responses against user feedback criteria
"""

import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from crewai import Agent, Task, Crew, Process
    from langchain_openai import ChatOpenAI
except ImportError:
    print("Warning: CrewAI or LangChain not installed. Run: pip install crewai langchain-openai")
    
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from .test_cases import TestCase, FeedbackCategory, ContextTestCase
except ImportError:
    # For direct execution
    from test_cases import TestCase, FeedbackCategory, ContextTestCase

@dataclass 
class EvaluationResult:
    """Result of an evaluation by a CrewAI agent"""
    agent_name: str
    test_case_id: str
    score: int  # 0-100
    passed: bool
    issues_found: List[str]
    recommendations: List[str]
    execution_time: float
    details: Dict[str, Any]

class ChatBotEvaluationCrew:
    """CrewAI crew for evaluating chatbot responses against user feedback"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")
        
        self.llm = ChatOpenAI(
            api_key=self.openai_api_key,
            model="gpt-4.1",
            temperature=0.1  # Low temperature for consistent evaluation
        )
        
        self.agents = self._create_agents()
    
    def _create_agents(self) -> Dict[str, Agent]:
        """Create specialized evaluation agents"""
        
        # BiocuratorLanguageDetector Agent
        biocurator_detector = Agent(
            role='Biocurator Language Detector',
            goal='Identify and flag biocurator-specific terminology and internal instructions in responses',
            backstory="""You are an expert at identifying internal biocurator language that should 
            not appear in depositor-facing responses. You have extensive knowledge of what language 
            is appropriate for external users vs internal staff.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # RedundancyAnalyzer Agent
        redundancy_analyzer = Agent(
            role='Redundancy Analyzer', 
            goal='Detect redundant sections and excessive verbosity in responses',
            backstory="""You are an expert in concise communication. You identify when responses 
            contain redundant Summary or Key Points sections that simply repeat the main content 
            without adding new value.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # ReferenceFormatter Agent
        reference_formatter = Agent(
            role='Reference Format Checker',
            goal='Evaluate reference formatting and identify raw ID displays vs clean citations',
            backstory="""You are an expert in documentation and citation formatting. You know 
            the difference between internal reference IDs that should be hidden and clean, 
            user-friendly citation formats.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # DepositorFocusEvaluator Agent
        depositor_focus = Agent(
            role='Depositor Focus Evaluator',
            goal='Ensure responses are focused on depositor needs and provide actionable guidance',
            backstory="""You are an expert in user experience and understand what information 
            is valuable to researchers depositing data vs internal process details that are 
            not relevant to external users.""",
            verbose=False,
            allow_delegation=False, 
            llm=self.llm
        )
        
        # QualityScorer Agent
        quality_scorer = Agent(
            role='Overall Quality Assessor',
            goal='Provide comprehensive quality assessment of responses including completeness and helpfulness',
            backstory="""You are an expert in evaluating the overall quality of technical support 
            responses. You assess completeness, accuracy, helpfulness, and user-friendliness.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        # ContextContinuityEvaluator Agent
        context_continuity = Agent(
            role='Context Continuity Evaluator',
            goal='Assess conversation context retention and evaluate follow-up question understanding',
            backstory="""You are an expert in conversational AI evaluation. You assess whether 
            responses demonstrate proper understanding of conversation context, pronoun resolution, 
            topic continuity, and appropriate reference to previous messages in multi-turn conversations.""",
            verbose=False,
            allow_delegation=False,
            llm=self.llm
        )
        
        return {
            'biocurator_detector': biocurator_detector,
            'redundancy_analyzer': redundancy_analyzer,
            'reference_formatter': reference_formatter, 
            'depositor_focus': depositor_focus,
            'quality_scorer': quality_scorer,
            'context_continuity': context_continuity
        }
    
    def evaluate_response(self, test_case: TestCase, response: str) -> List[EvaluationResult]:
        """Evaluate a chatbot response using all relevant agents"""
        
        results = []
        start_time = datetime.now()
        
        # Create evaluation tasks based on test case category
        tasks = self._create_evaluation_tasks(test_case, response)
        
        # Execute each task
        for task_info in tasks:
            agent_name = task_info['agent_name']
            task = task_info['task']
            agent = self.agents[agent_name]
            
            try:
                # Create a crew with single agent and task
                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=False
                )
                
                # Execute the evaluation
                task_start = datetime.now()
                result = crew.kickoff()
                execution_time = (datetime.now() - task_start).total_seconds()
                
                # Parse result into EvaluationResult
                eval_result = self._parse_agent_result(
                    agent_name, test_case.id, result, execution_time, test_case, response
                )
                results.append(eval_result)
                
            except Exception as e:
                # Handle agent execution errors
                error_result = EvaluationResult(
                    agent_name=agent_name,
                    test_case_id=test_case.id,
                    score=0,
                    passed=False,
                    issues_found=[f"Agent execution error: {str(e)}"],
                    recommendations=["Review agent configuration and try again"],
                    execution_time=0.0,
                    details={"error": str(e)}
                )
                results.append(error_result)
        
        return results
    
    def _create_evaluation_tasks(self, test_case: TestCase, response: str) -> List[Dict[str, Any]]:
        """Create evaluation tasks based on test case category and requirements"""
        
        tasks = []
        
        # BiocuratorLanguageDetector - for biocurator language issues
        if (test_case.category == FeedbackCategory.BIOCURATOR_LANGUAGE or 
            test_case.category == FeedbackCategory.INTERNAL_INSTRUCTIONS):
            
            task = Task(
                description=f"""Analyze this chatbot response for biocurator-specific language and internal instructions:
                
                TEST CASE: {test_case.description}
                FORBIDDEN CONTENT: {', '.join(test_case.forbidden_content)}
                
                RESPONSE TO ANALYZE:
                {response}
                
                Evaluate:
                1. Presence of forbidden biocurator terms
                2. Internal instructions that should not be shown to depositors
                3. Use of depositor-appropriate language instead
                
                Provide:
                - Score (0-100, where 100 = completely clean)
                - List of specific forbidden terms found (if any)
                - Recommendations for improvement
                """,
                agent=self.agents['biocurator_detector'],
                expected_output="Score, identified issues, and recommendations"
            )
            
            tasks.append({
                'agent_name': 'biocurator_detector',
                'task': task
            })
        
        # RedundancyAnalyzer - for verbosity and redundancy issues
        if test_case.category == FeedbackCategory.REDUNDANCY:
            
            task = Task(
                description=f"""Analyze this response for redundancy and excessive verbosity:
                
                TEST CASE: {test_case.description}
                FORBIDDEN SECTIONS: {', '.join(test_case.forbidden_content)}
                MAX LENGTH: {test_case.max_response_length or 'No limit'}
                
                RESPONSE TO ANALYZE:
                {response}
                
                Evaluate:
                1. Presence of redundant Summary or Key Points sections
                2. Whether sections add new information or just repeat content
                3. Overall conciseness and focus
                
                Provide:
                - Conciseness score (0-100, where 100 = perfectly concise)
                - Identified redundant sections
                - Suggestions for streamlining
                """,
                agent=self.agents['redundancy_analyzer'],
                expected_output="Conciseness score, redundant sections, and improvement suggestions"
            )
            
            tasks.append({
                'agent_name': 'redundancy_analyzer',
                'task': task
            })
        
        # ReferenceFormatter - for reference formatting issues  
        if test_case.category == FeedbackCategory.REFERENCES:
            
            task = Task(
                description=f"""Analyze reference formatting in this response:
                
                TEST CASE: {test_case.description}  
                FORBIDDEN FORMATS: {', '.join(test_case.forbidden_content)}
                REQUIRED FORMATS: {', '.join(test_case.required_content)}
                
                RESPONSE TO ANALYZE:
                {response}
                
                Evaluate:
                1. Presence of raw reference IDs like [ID:0], [ID:1]
                2. Use of clean citation formats
                3. Appropriateness for external users
                
                Provide:
                - Reference quality score (0-100)
                - Raw reference IDs found (if any)  
                - Recommendations for clean formatting
                """,
                agent=self.agents['reference_formatter'],
                expected_output="Reference quality score, formatting issues, and recommendations"
            )
            
            tasks.append({
                'agent_name': 'reference_formatter', 
                'task': task
            })
        
        # DepositorFocusEvaluator - for depositor appropriateness
        if (test_case.category == FeedbackCategory.DEPOSITOR_FOCUS or
            test_case.category == FeedbackCategory.COMPLETENESS):
            
            task = Task(
                description=f"""Evaluate how well this response serves depositor needs:
                
                TEST CASE: {test_case.description}
                QUESTION: {test_case.question}
                REQUIRED CONTENT: {', '.join(test_case.required_content)}
                
                RESPONSE TO ANALYZE:
                {response}
                
                Evaluate:
                1. Relevance and usefulness for depositors
                2. Actionable guidance provided
                3. Completeness of information
                4. External user appropriateness
                
                Provide:
                - Depositor focus score (0-100)
                - Missing actionable elements
                - Suggestions for better depositor service
                """,
                agent=self.agents['depositor_focus'],
                expected_output="Depositor focus score, gaps identified, and improvement suggestions"
            )
            
            tasks.append({
                'agent_name': 'depositor_focus',
                'task': task
            })
        
        # QualityScorer - always run for overall assessment
        task = Task(
            description=f"""Provide overall quality assessment of this chatbot response:
            
            TEST CASE: {test_case.question}
            USER SOURCE: {test_case.user_source}
            SEVERITY: {test_case.severity.value}
            
            RESPONSE TO ANALYZE:
            {response}
            
            Evaluate overall:
            1. Completeness and accuracy
            2. Helpfulness to the user
            3. Professional quality
            4. Achievement of test case requirements
            
            Provide:
            - Overall quality score (0-100)
            - Key strengths and weaknesses  
            - Priority recommendations
            """,
            agent=self.agents['quality_scorer'],
            expected_output="Overall quality score, strengths/weaknesses, and recommendations"
        )
        
        tasks.append({
            'agent_name': 'quality_scorer',
            'task': task
        })
        
        return tasks
    
    def _parse_agent_result(self, agent_name: str, test_case_id: str, raw_result: str, 
                          execution_time: float, test_case: TestCase, response: str) -> EvaluationResult:
        """Parse agent result into structured EvaluationResult"""
        
        # Default values
        score = 50
        issues_found = []
        recommendations = []
        passed = True
        
        result_text = str(raw_result)
        
        try:
            # Extract score using regex patterns
            score_patterns = [
                r'score[:\s]+(\d+)',
                r'(\d+)/100',
                r'(\d+)%',
                r'Score:\s*(\d+)'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, result_text, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    break
            
            # Extract issues and recommendations from result text
            if 'issue' in result_text.lower() or 'problem' in result_text.lower():
                issues_found.append("Issues identified by agent - see details")
            
            if 'recommend' in result_text.lower() or 'suggest' in result_text.lower():
                recommendations.append("Recommendations provided by agent - see details")
            
            # Check against forbidden content for binary pass/fail
            if test_case.forbidden_content:
                for forbidden in test_case.forbidden_content:
                    if forbidden.lower() in response.lower():
                        issues_found.append(f"Forbidden content found: {forbidden}")
                        passed = False
            
            # Adjust passed status based on score
            if score < 70:
                passed = False
                
        except Exception as e:
            issues_found.append(f"Error parsing result: {str(e)}")
            passed = False
        
        return EvaluationResult(
            agent_name=agent_name,
            test_case_id=test_case_id,
            score=max(0, min(100, score)),  # Clamp to 0-100
            passed=passed,
            issues_found=issues_found,
            recommendations=recommendations,
            execution_time=execution_time,
            details={
                'raw_result': result_text,
                'test_category': test_case.category.value,
                'test_severity': test_case.severity.value
            }
        )
    
    def evaluate_context_continuity(self, context_test: ContextTestCase, conversation_history: List[str]) -> List[EvaluationResult]:
        """
        Evaluate context continuity across multiple messages in a conversation
        
        Args:
            context_test: ContextTestCase with multiple questions
            conversation_history: List of responses corresponding to each question
            
        Returns:
            List of EvaluationResult objects for each response in the conversation
        """
        results = []
        
        if len(conversation_history) != len(context_test.questions):
            # Return error if conversation history doesn't match questions
            error_result = EvaluationResult(
                agent_name="context_continuity",
                test_case_id=context_test.id,
                score=0,
                passed=False,
                issues_found=[f"Conversation length mismatch: {len(conversation_history)} responses vs {len(context_test.questions)} questions"],
                recommendations=["Ensure all questions in context test are answered"],
                execution_time=0.0,
                details={"error": "conversation_length_mismatch"}
            )
            return [error_result]
        
        # Evaluate each response in the context of the conversation
        for i, (question, response) in enumerate(zip(context_test.questions, conversation_history)):
            try:
                # Build conversation context for evaluation
                conversation_context = ""
                for j in range(i + 1):
                    conversation_context += f"Q{j+1}: {context_test.questions[j]}\nA{j+1}: {conversation_history[j]}\n\n"
                
                # Create context continuity evaluation task
                task = Task(
                    description=f"""Evaluate context continuity for this multi-turn conversation:

TEST CASE: {context_test.description}
CONTEXT EXPECTATIONS: {', '.join(context_test.context_expectations)}
FORBIDDEN RESPONSES: {', '.join(context_test.forbidden_responses)}
REQUIRED RESPONSES: {', '.join(context_test.required_responses)}

FULL CONVERSATION:
{conversation_context}

CURRENT QUESTION ({i+1}/{len(context_test.questions)}): {question}
CURRENT RESPONSE TO EVALUATE: {response}

Evaluate this response for:
1. Context retention from previous messages (if applicable)
2. Proper understanding of pronouns and references
3. Topic continuity and coherence
4. Appropriate use of previous conversation information
5. Absence of context-loss indicators

For Question 1, focus on initial response quality.
For Questions 2+, heavily weight context continuity and reference resolution.

Provide:
- Context continuity score (0-100, where 100 = perfect context retention)
- Specific examples of context retention or loss
- Recommendations for improvement
""",
                    agent=self.agents['context_continuity'],
                    expected_output="Context continuity score, specific examples, and recommendations"
                )
                
                # Execute evaluation
                task_start = datetime.now()
                crew = Crew(
                    agents=[self.agents['context_continuity']],
                    tasks=[task],
                    process=Process.sequential,
                    verbose=False
                )
                
                result = crew.kickoff()
                execution_time = (datetime.now() - task_start).total_seconds()
                
                # Parse result into EvaluationResult
                eval_result = self._parse_context_result(
                    context_test.id, result, execution_time, context_test, 
                    question, response, i + 1
                )
                results.append(eval_result)
                
            except Exception as e:
                error_result = EvaluationResult(
                    agent_name="context_continuity",
                    test_case_id=context_test.id,
                    score=0,
                    passed=False,
                    issues_found=[f"Context evaluation error for Q{i+1}: {str(e)}"],
                    recommendations=["Review context evaluation setup"],
                    execution_time=0.0,
                    details={"error": str(e), "question_number": i + 1}
                )
                results.append(error_result)
        
        return results
    
    def _parse_context_result(self, test_case_id: str, raw_result: str, execution_time: float, 
                            context_test: ContextTestCase, question: str, response: str, 
                            question_number: int) -> EvaluationResult:
        """Parse context evaluation result into structured EvaluationResult"""
        
        # Default values
        score = 50
        issues_found = []
        recommendations = []
        passed = True
        
        result_text = str(raw_result)
        
        try:
            # Extract score using regex patterns
            score_patterns = [
                r'context.*?score[:\s]+(\d+)',
                r'continuity.*?score[:\s]+(\d+)',
                r'score[:\s]+(\d+)',
                r'(\d+)/100',
                r'(\d+)%'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, result_text, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    break
            
            # Check for context loss indicators in the response
            for forbidden in context_test.forbidden_responses:
                if forbidden.lower() in response.lower():
                    issues_found.append(f"Context loss indicator found: {forbidden}")
                    passed = False
                    score = max(0, score - 20)  # Penalty for context loss
            
            # Check for required context indicators
            required_found = 0
            for required in context_test.required_responses:
                if required.lower() in response.lower():
                    required_found += 1
            
            if context_test.required_responses:
                context_coverage = required_found / len(context_test.required_responses)
                if context_coverage < 0.5:
                    issues_found.append(f"Low context coverage: {context_coverage:.1%}")
                    passed = False
            
            # Adjust passed status based on score
            if score < 70:
                passed = False
                
            # Extract issues and recommendations from result text
            if 'issue' in result_text.lower() or 'problem' in result_text.lower():
                issues_found.append("Context issues identified by agent - see details")
            
            if 'recommend' in result_text.lower() or 'suggest' in result_text.lower():
                recommendations.append("Context improvement recommendations provided - see details")
                
        except Exception as e:
            issues_found.append(f"Error parsing context result: {str(e)}")
            passed = False
        
        return EvaluationResult(
            agent_name="context_continuity",
            test_case_id=f"{test_case_id}_Q{question_number}",
            score=max(0, min(100, score)),
            passed=passed,
            issues_found=issues_found,
            recommendations=recommendations,
            execution_time=execution_time,
            details={
                'raw_result': result_text,
                'question_number': question_number,
                'question': question,
                'test_category': context_test.category.value,
                'test_severity': context_test.severity.value,
                'context_expectations': context_test.context_expectations
            }
        )

# Factory function to create CrewAI evaluator
def create_evaluator() -> ChatBotEvaluationCrew:
    """Create CrewAI evaluation crew for RAGFlow chatbot testing"""
    return ChatBotEvaluationCrew()

# Example usage
if __name__ == "__main__":
    from test_cases import UserFeedbackTestSuite
    
    # Test the CrewAI evaluator with RAGFlow chatbot responses
    test_suite = UserFeedbackTestSuite()
    evaluator = create_evaluator()
    
    # Get a sample test case
    test_case = test_suite.test_cases[0]  # BRIAN_001
    
    # Sample RAGFlow response with issues (what the old system might produce)
    sample_response = """
    To resolve this issue, you need to contact Ezra who can help with ORCID login issues.
    
    ## Summary
    Contact Ezra for ORCID assistance.
    
    ## Key Points:
    - Ezra can help with ORCID login
    - This is a biocurator process
    
    References: [ID:0] [ID:1] [ID:2]
    """
    
    print(f"Testing RAGFlow Response for: {test_case.question}")
    print(f"Expected issues to detect: {test_case.forbidden_content}")
    
    results = evaluator.evaluate_response(test_case, sample_response)
    
    for result in results:
        print(f"\n{result.agent_name}: Score {result.score}/100, Passed: {result.passed}")
        if result.issues_found:
            print(f"Issues detected: {result.issues_found}")
        if result.recommendations:
            print(f"Recommendations: {result.recommendations}")