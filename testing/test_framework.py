#!/usr/bin/env python3
"""
RCSB PDB ChatBot Testing Framework
Main orchestrator with Rich console interface for systematic testing and evaluation
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.prompt import Prompt, Confirm
    from rich import box
except ImportError:
    print("Rich library not installed. Run: pip install rich")
    sys.exit(1)

try:
    from .test_cases import UserFeedbackTestSuite, TestCase, Severity, FeedbackCategory
    from .crewai_evaluators import create_evaluator, EvaluationResult
except ImportError:
    # For direct execution
    from test_cases import UserFeedbackTestSuite, TestCase, Severity, FeedbackCategory
    from crewai_evaluators import create_evaluator, EvaluationResult

# Import session manager
try:
    from src.user_session_manager import UserSessionManager
    from src.ragflow_assistant_manager import create_assistant_manager
except ImportError as e:
    print(f"Could not import session manager: {e}")
    print("Make sure you have the required dependencies installed:")
    print("  pip install -r requirements.txt")
    print("And that you're running from the project root directory.")
    sys.exit(1)

class RichTestFramework:
    """Main testing framework with Rich console interface"""
    
    def __init__(self):
        self.console = Console()
        self.test_suite = UserFeedbackTestSuite()
        self.evaluator = create_evaluator()
        self.session_manager = None
        self.test_user_id = "test_user_automated"
        self.test_chat_id = None
        self.results_dir = Path("testing/results")
        self.reports_dir = Path("testing/reports")
        
        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Test execution state
        self.current_test_results = []
        self.execution_start_time = None
        
    def initialize_chatbot_connection(self) -> bool:
        """Initialize connection to the RAGFlow chatbot system"""
        
        with self.console.status("[bold blue]Initializing RAGFlow connection..."):
            try:
                # Get environment variables
                api_key = os.getenv('RAGFLOW_API_KEY')
                base_url = os.getenv('RAGFLOW_BASE_URL', 'http://127.0.0.1:9380')
                
                if not api_key:
                    self.console.print("[red]❌ RAGFLOW_API_KEY not found in environment variables")
                    return False
                
                # Initialize session manager
                self.session_manager = UserSessionManager(
                    api_key=api_key,
                    base_url=base_url,
                    data_dir="testing/test_data"
                )
                
                # Create test chat
                test_chat = self.session_manager.create_user_chat(
                    self.test_user_id, 
                    f"Testing Session {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                self.test_chat_id = test_chat.chat_id
                
                self.console.print("[green]✅ RAGFlow connection initialized successfully")
                self.console.print(f"[dim]Test User: {self.test_user_id}")
                self.console.print(f"[dim]Test Chat: {self.test_chat_id}")
                return True
                
            except Exception as e:
                self.console.print(f"[red]❌ Failed to initialize RAGFlow connection: {e}")
                return False
    
    def display_welcome(self):
        """Display welcome banner and system information"""
        
        title = Text("🧪 RCSB PDB ChatBot Testing Framework", style="bold blue")
        
        welcome_panel = Panel(
            f"""[green]Automated Testing System for User Feedback Validation[/green]
            
📋 Test Suite: {len(self.test_suite.test_cases)} test cases
🤖 Evaluators: CrewAI agents + Rule-based fallback
📊 Categories: {len(set(tc.category for tc in self.test_suite.test_cases))} feedback categories
⚖️ Severity levels: Critical, High, Medium, Low

[dim]Ready to systematically validate chatbot improvements against user feedback.[/dim]""",
            title=title,
            border_style="blue"
        )
        
        self.console.print(welcome_panel)
        self.console.print()
    
    def display_test_summary(self):
        """Display summary of available tests"""
        
        summary = self.test_suite.get_test_summary()
        
        # Create summary table
        summary_table = Table(title="Test Suite Overview", box=box.ROUNDED)
        summary_table.add_column("Category", style="cyan")
        summary_table.add_column("Count", justify="right", style="magenta")
        summary_table.add_column("Description", style="white")
        
        category_descriptions = {
            "biocurator_language": "Internal terminology detection",
            "redundancy": "Verbosity and redundant sections",
            "references": "Citation formatting quality",
            "depositor_focus": "User-appropriate guidance",
            "completeness": "Information completeness",
            "internal_instructions": "Internal process filtering"
        }
        
        for category, count in summary['by_category'].items():
            description = category_descriptions.get(category, "General validation")
            summary_table.add_row(
                category.replace('_', ' ').title(),
                str(count),
                description
            )
        
        self.console.print(summary_table)
        self.console.print()
        
        # Severity breakdown
        severity_table = Table(title="Tests by Severity", box=box.SIMPLE)
        severity_table.add_column("Severity", style="bold")
        severity_table.add_column("Count", justify="right")
        severity_table.add_column("Priority", style="italic")
        
        severity_colors = {
            "critical": "red", 
            "high": "orange3",
            "medium": "yellow",
            "low": "green"
        }
        
        for severity, count in summary['by_severity'].items():
            color = severity_colors.get(severity, "white")
            priority = "🔴 Must Fix" if severity == "critical" else "🟡 Important" if severity == "high" else "🟢 Nice to Have"
            severity_table.add_row(
                f"[{color}]{severity.upper()}[/{color}]",
                str(count),
                priority
            )
        
        self.console.print(severity_table)
        self.console.print()
    
    def run_single_test(self, test_case: TestCase) -> Dict[str, Any]:
        """Run a single test case and return results"""
        
        test_start_time = datetime.now()
        
        try:
            # Send question to chatbot
            response_content = ""
            response_references = []
            
            # Collect streaming response
            for response_chunk in self.session_manager.send_message_to_chat(
                self.test_user_id,
                self.test_chat_id, 
                test_case.question
            ):
                response_content = response_chunk.content
                if response_chunk.references:
                    response_references = response_chunk.references
            
            # Evaluate response using CrewAI agents
            evaluation_results = self.evaluator.evaluate_response(test_case, response_content)
            
            # Calculate overall score
            if evaluation_results:
                overall_score = sum(result.score for result in evaluation_results) / len(evaluation_results)
            else:
                overall_score = 0
            
            # Determine overall pass/fail
            overall_passed = all(result.passed for result in evaluation_results)
            
            execution_time = (datetime.now() - test_start_time).total_seconds()
            
            return {
                'test_case': test_case,
                'response': response_content,
                'references': response_references,
                'evaluation_results': evaluation_results,
                'overall_score': overall_score,
                'overall_passed': overall_passed,
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'test_case': test_case,
                'response': "",
                'references': [],
                'evaluation_results': [],
                'overall_score': 0,
                'overall_passed': False,
                'execution_time': (datetime.now() - test_start_time).total_seconds(),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_test_suite(self, test_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Run the complete test suite with Rich progress display"""
        
        # Filter tests if requested
        if test_filter:
            if test_filter.lower() == "critical":
                tests_to_run = self.test_suite.get_critical_tests()
            elif test_filter.lower() in ["brian", "chenghua", "irina", "gregg", "sutapa"]:
                tests_to_run = self.test_suite.get_tests_by_user(test_filter)
            else:
                tests_to_run = self.test_suite.test_cases
        else:
            tests_to_run = self.test_suite.test_cases
        
        self.execution_start_time = datetime.now()
        self.current_test_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            # Create progress task
            test_task = progress.add_task(
                f"[cyan]Running {len(tests_to_run)} test cases...",
                total=len(tests_to_run)
            )
            
            for i, test_case in enumerate(tests_to_run, 1):
                # Update progress description
                progress.update(
                    test_task, 
                    description=f"[cyan]Testing {test_case.id}: {test_case.question[:50]}..."
                )
                
                # Run the test
                result = self.run_single_test(test_case)
                self.current_test_results.append(result)
                
                # Update progress
                progress.update(test_task, advance=1)
                
                # Brief pause for visual effect
                time.sleep(0.1)
        
        return self.current_test_results
    
    def display_results_summary(self, results: List[Dict[str, Any]]):
        """Display comprehensive results summary with Rich formatting"""
        
        if not results:
            self.console.print("[red]No results to display")
            return
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get('overall_passed', False))
        failed_tests = total_tests - passed_tests
        avg_score = sum(r.get('overall_score', 0) for r in results) / total_tests if results else 0
        
        # Overall summary panel
        summary_text = f"""[green]✅ Passed: {passed_tests}[/green] | [red]❌ Failed: {failed_tests}[/red] | [blue]📊 Avg Score: {avg_score:.1f}/100[/blue]

[dim]Execution time: {(datetime.now() - self.execution_start_time).total_seconds():.1f} seconds[/dim]"""
        
        summary_panel = Panel(
            summary_text,
            title="[bold]Test Execution Summary",
            border_style="green" if failed_tests == 0 else "red"
        )
        
        self.console.print(summary_panel)
        self.console.print()
        
        # Detailed results table
        results_table = Table(title="Detailed Test Results", box=box.ROUNDED)
        results_table.add_column("Test ID", style="cyan", width=12)
        results_table.add_column("Category", style="blue", width=15) 
        results_table.add_column("User", style="magenta", width=10)
        results_table.add_column("Score", justify="right", style="bold", width=8)
        results_table.add_column("Status", justify="center", width=8)
        results_table.add_column("Issues", style="yellow", width=30)
        
        for result in results:
            test_case = result['test_case']
            score = result.get('overall_score', 0)
            passed = result.get('overall_passed', False)
            
            # Collect issues from evaluation results
            all_issues = []
            for eval_result in result.get('evaluation_results', []):
                all_issues.extend(eval_result.issues_found)
            
            issues_text = "; ".join(all_issues[:2])  # Show first 2 issues
            if len(all_issues) > 2:
                issues_text += f" (+{len(all_issues)-2} more)"
            
            status = "🟢 PASS" if passed else "🔴 FAIL"
            score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            
            results_table.add_row(
                test_case.id,
                test_case.category.value.replace('_', ' ').title(),
                test_case.user_source,
                f"[{score_color}]{score:.0f}/100[/{score_color}]",
                status,
                issues_text[:30] + "..." if len(issues_text) > 30 else issues_text
            )
        
        self.console.print(results_table)
        self.console.print()
        
        # Category breakdown
        self._display_category_breakdown(results)
        
        # Critical failures
        critical_failures = [r for r in results 
                           if not r.get('overall_passed', False) 
                           and r['test_case'].severity == Severity.CRITICAL]
        
        if critical_failures:
            self.console.print("[bold red]🚨 Critical Test Failures:[/bold red]")
            for failure in critical_failures:
                tc = failure['test_case']
                self.console.print(f"  • [red]{tc.id}[/red]: {tc.description}")
            self.console.print()
    
    def _display_category_breakdown(self, results: List[Dict[str, Any]]):
        """Display results breakdown by category"""
        
        category_stats = {}
        
        for result in results:
            category = result['test_case'].category.value
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'passed': 0, 'total_score': 0}
            
            category_stats[category]['total'] += 1
            category_stats[category]['total_score'] += result.get('overall_score', 0)
            if result.get('overall_passed', False):
                category_stats[category]['passed'] += 1
        
        # Category performance table
        category_table = Table(title="Performance by Category", box=box.SIMPLE)
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Pass Rate", justify="right", style="green")
        category_table.add_column("Avg Score", justify="right", style="blue")
        category_table.add_column("Status", justify="center")
        
        for category, stats in category_stats.items():
            pass_rate = (stats['passed'] / stats['total']) * 100
            avg_score = stats['total_score'] / stats['total']
            
            status = "🟢 Good" if pass_rate >= 80 else "🟡 Review" if pass_rate >= 60 else "🔴 Fix"
            
            category_table.add_row(
                category.replace('_', ' ').title(),
                f"{pass_rate:.0f}%",
                f"{avg_score:.0f}/100", 
                status
            )
        
        self.console.print(category_table)
        self.console.print()
    
    def save_results(self, results: List[Dict[str, Any]], filename: Optional[str] = None):
        """Save test results to file"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_{timestamp}.json"
        
        filepath = self.results_dir / filename
        
        # Prepare results for JSON serialization
        serializable_results = []
        for result in results:
            # Convert test case to dict
            test_case_dict = {
                'id': result['test_case'].id,
                'question': result['test_case'].question,
                'category': result['test_case'].category.value,
                'severity': result['test_case'].severity.value,
                'user_source': result['test_case'].user_source,
                'description': result['test_case'].description,
                'forbidden_content': result['test_case'].forbidden_content,
                'required_content': result['test_case'].required_content
            }
            
            # Convert evaluation results
            eval_results = []
            for eval_result in result.get('evaluation_results', []):
                eval_results.append({
                    'agent_name': eval_result.agent_name,
                    'score': eval_result.score,
                    'passed': eval_result.passed,
                    'issues_found': eval_result.issues_found,
                    'recommendations': eval_result.recommendations,
                    'execution_time': eval_result.execution_time
                })
            
            serializable_result = {
                'test_case': test_case_dict,
                'response': result.get('response', ''),
                'evaluation_results': eval_results,
                'overall_score': result.get('overall_score', 0),
                'overall_passed': result.get('overall_passed', False),
                'execution_time': result.get('execution_time', 0),
                'timestamp': result.get('timestamp', datetime.now().isoformat()),
                'error': result.get('error')
            }
            
            serializable_results.append(serializable_result)
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump({
                'metadata': {
                    'framework_version': '1.0.0',
                    'execution_time': datetime.now().isoformat(),
                    'total_tests': len(results),
                    'test_filter': getattr(self, 'current_filter', None)
                },
                'results': serializable_results
            }, f, indent=2)
        
        self.console.print(f"[green]💾 Results saved to: {filepath}")
    
    def interactive_menu(self):
        """Display interactive menu for test execution options"""
        
        while True:
            self.console.print("\n[bold blue]🧪 Test Framework Menu[/bold blue]")
            self.console.print("1. Run all tests")
            self.console.print("2. Run critical tests only")
            self.console.print("3. Run tests by user feedback (Brian, Chenghua, etc.)")
            self.console.print("4. View test suite summary")
            self.console.print("5. View previous results")
            self.console.print("6. Exit")
            
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6"], default="1")
            
            if choice == "1":
                results = self.run_test_suite()
                self.display_results_summary(results)
                if Confirm.ask("Save results?"):
                    self.save_results(results)
                    
            elif choice == "2":
                results = self.run_test_suite("critical")
                self.display_results_summary(results)
                if Confirm.ask("Save results?"):
                    self.save_results(results)
                    
            elif choice == "3":
                user = Prompt.ask("Enter user name", choices=["brian", "chenghua", "irina", "gregg", "sutapa"])
                results = self.run_test_suite(user)
                self.display_results_summary(results)
                if Confirm.ask("Save results?"):
                    self.save_results(results)
                    
            elif choice == "4":
                self.display_test_summary()
                
            elif choice == "5":
                self._view_previous_results()
                
            elif choice == "6":
                self.console.print("[green]👋 Goodbye!")
                break
    
    def _view_previous_results(self):
        """View previous test results"""
        
        result_files = list(self.results_dir.glob("test_results_*.json"))
        
        if not result_files:
            self.console.print("[yellow]No previous results found")
            return
        
        # Show available files
        self.console.print("\n[bold]Previous Results:[/bold]")
        for i, filepath in enumerate(result_files[-10:], 1):  # Show last 10
            timestamp = filepath.stem.replace("test_results_", "")
            self.console.print(f"{i}. {timestamp}")
        
        try:
            selection = int(Prompt.ask("Select file number")) - 1
            if 0 <= selection < len(result_files[-10:]):
                selected_file = result_files[-(10-selection)]
                
                with open(selected_file) as f:
                    data = json.load(f)
                
                self.console.print(f"\n[green]📄 Results from: {data['metadata']['execution_time']}")
                self.console.print(f"Total tests: {data['metadata']['total_tests']}")
                
                # Convert back to display format (simplified)
                results_summary = data['results']
                passed = sum(1 for r in results_summary if r['overall_passed'])
                failed = len(results_summary) - passed
                avg_score = sum(r['overall_score'] for r in results_summary) / len(results_summary)
                
                self.console.print(f"Passed: {passed}, Failed: {failed}, Average Score: {avg_score:.1f}")
                
        except (ValueError, IndexError, FileNotFoundError) as e:
            self.console.print(f"[red]Error loading results: {e}")

def main():
    """Main entry point for the testing framework"""
    
    framework = RichTestFramework()
    
    # Display welcome
    framework.display_welcome()
    
    # Initialize chatbot connection
    if not framework.initialize_chatbot_connection():
        framework.console.print("[red]Cannot proceed without chatbot connection. Check your configuration.")
        return 1
    
    # Show test summary
    framework.display_test_summary()
    
    # Run interactive menu
    framework.interactive_menu()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())