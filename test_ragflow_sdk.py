#!/usr/bin/env python3
"""
RAGFlow SDK Testing Script
Tests all functionality with the existing 'RCSB ChatBot v2' assistant
"""

import sys
import time
from typing import Optional, List, Dict, Any

try:
    from ragflow_sdk import RAGFlow
except ImportError:
    print("❌ RAGFlow SDK not installed. Run: pip install ragflow-sdk")
    sys.exit(1)

# Configuration
API_KEY = "ragflow-VjNjM4Zjk0NmMyZDExZjA4MjQyNTY3YT"
BASE_URL = "http://127.0.0.1:9380"  # Default RAGFlow port
ASSISTANT_NAME = "RCSB ChatBot v2"

class RAGFlowTester:
    """Comprehensive testing class for RAGFlow SDK"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.rag_client = None
        self.assistant = None
        self.test_session = None
        
    def test_connection(self) -> bool:
        """Test basic connection to RAGFlow"""
        print("🔌 Testing RAGFlow connection...")
        
        try:
            self.rag_client = RAGFlow(api_key=self.api_key, base_url=self.base_url)
            print(f"✅ RAGFlow client initialized successfully")
            print(f"   - API Key: {self.api_key[:20]}...")
            print(f"   - Base URL: {self.base_url}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize RAGFlow client: {e}")
            return False
    
    def test_list_assistants(self) -> bool:
        """Test listing chat assistants and find RCSB ChatBot v2"""
        print("\n📋 Testing chat assistant listing...")
        
        try:
            assistants = self.rag_client.list_chats()
            print(f"✅ Found {len(assistants)} chat assistant(s)")
            
            # Display all assistants
            for i, assistant in enumerate(assistants, 1):
                print(f"   {i}. Name: '{assistant.name}' | ID: {assistant.id}")
            
            # Find RCSB ChatBot v2
            target_assistant = None
            for assistant in assistants:
                if assistant.name == ASSISTANT_NAME:
                    target_assistant = assistant
                    break
            
            if target_assistant:
                self.assistant = target_assistant
                print(f"🎯 Found target assistant: '{ASSISTANT_NAME}'")
                print(f"   - ID: {self.assistant.id}")
                print(f"   - Dataset IDs: {getattr(self.assistant, 'dataset_ids', 'Unknown')}")
                return True
            else:
                print(f"❌ Assistant '{ASSISTANT_NAME}' not found!")
                print("Available assistants:")
                for assistant in assistants:
                    print(f"   - '{assistant.name}'")
                return False
                
        except Exception as e:
            print(f"❌ Failed to list chat assistants: {e}")
            return False
    
    def test_create_session(self) -> bool:
        """Test creating a new chat session"""
        print(f"\n🆕 Testing session creation with '{ASSISTANT_NAME}'...")
        
        try:
            session_name = f"Test Session {int(time.time())}"
            self.test_session = self.assistant.create_session(name=session_name)
            
            print(f"✅ Session created successfully")
            print(f"   - Session ID: {self.test_session.id}")
            print(f"   - Session Name: {self.test_session.name}")
            print(f"   - Chat ID: {getattr(self.test_session, 'chat_id', 'Unknown')}")
            
            # Check initial message
            if hasattr(self.test_session, 'message') and self.test_session.message:
                print(f"   - Initial Message: {self.test_session.message[0]['content'][:50]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
            return False
    
    def test_list_sessions(self) -> bool:
        """Test listing sessions for the assistant"""
        print(f"\n📝 Testing session listing for '{ASSISTANT_NAME}'...")
        
        try:
            sessions = self.assistant.list_sessions()
            print(f"✅ Found {len(sessions)} session(s)")
            
            for i, session in enumerate(sessions[:5], 1):  # Show first 5
                print(f"   {i}. '{session.name}' | ID: {session.id[:8]}...")
            
            if len(sessions) > 5:
                print(f"   ... and {len(sessions) - 5} more sessions")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to list sessions: {e}")
            return False
    
    def test_basic_chat(self) -> bool:
        """Test basic chat functionality"""
        print(f"\n💬 Testing basic chat with '{ASSISTANT_NAME}'...")
        
        try:
            test_question = "Hello! Can you introduce yourself?"
            print(f"📤 Sending: '{test_question}'")
            
            # Test non-streaming response - it seems to always return a generator
            response_generator = self.test_session.ask(question=test_question, stream=False)
            
            # Get the final response from generator
            final_response = None
            for response in response_generator:
                final_response = response
            
            if final_response:
                print(f"📥 Response received:")
                print(f"   - Content: {final_response.content[:100]}...")
                print(f"   - Message ID: {getattr(final_response, 'id', 'Unknown')}")
                
                # Check for references
                if hasattr(final_response, 'reference') and final_response.reference:
                    print(f"   - References: {len(final_response.reference)} chunk(s)")
                    for i, ref in enumerate(final_response.reference[:2], 1):  # Show first 2
                        print(f"     {i}. Document: {ref.get('document_name', 'Unknown')}")
                        print(f"        Content: {ref.get('content', '')[:50]}...")
                else:
                    print(f"   - References: None")
                
                return True
            else:
                print("❌ No response received")
                return False
            
        except Exception as e:
            print(f"❌ Failed basic chat test: {e}")
            return False
    
    def test_streaming_chat(self) -> bool:
        """Test streaming chat functionality"""
        print(f"\n📡 Testing streaming chat with '{ASSISTANT_NAME}'...")
        
        try:
            test_question = "What can you help me with?"
            print(f"📤 Sending: '{test_question}'")
            print("📥 Streaming response:")
            
            full_content = ""
            chunk_count = 0
            
            for chunk in self.test_session.ask(question=test_question, stream=True):
                new_content = chunk.content[len(full_content):]
                if new_content:
                    print(new_content, end='', flush=True)
                    full_content = chunk.content
                    chunk_count += 1
            
            print(f"\n✅ Streaming completed")
            print(f"   - Total chunks: {chunk_count}")
            print(f"   - Final content length: {len(full_content)} characters")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed streaming chat test: {e}")
            return False
    
    def test_conversation_flow(self) -> bool:
        """Test multi-turn conversation"""
        print(f"\n🔄 Testing conversation flow with '{ASSISTANT_NAME}'...")
        
        try:
            questions = [
                "What is RCSB PDB?",
                "Can you tell me more about protein structures?",
                "How can I search for structures in the database?"
            ]
            
            for i, question in enumerate(questions, 1):
                print(f"\n   Turn {i}: '{question}'")
                
                # Handle generator response
                response_generator = self.test_session.ask(question=question, stream=False)
                final_response = None
                for response in response_generator:
                    final_response = response
                
                if final_response:
                    print(f"   Response: {final_response.content[:80]}...")
                else:
                    print(f"   No response received")
                
                # Small delay between questions
                time.sleep(1)
            
            print(f"\n✅ Conversation flow test completed")
            return True
            
        except Exception as e:
            print(f"❌ Failed conversation flow test: {e}")
            return False
    
    def test_session_management(self) -> bool:
        """Test advanced session management"""
        print(f"\n⚙️ Testing session management...")
        
        try:
            # Create another session
            session2 = self.assistant.create_session(name="Test Session 2")
            print(f"✅ Created second session: {session2.id}")
            
            # Test both sessions with generator handling
            response1_gen = self.test_session.ask("What's my first question?", stream=False)
            response1 = None
            for resp in response1_gen:
                response1 = resp
            
            response2_gen = session2.ask("This is my first question in session 2", stream=False)
            response2 = None
            for resp in response2_gen:
                response2 = resp
            
            if response1:
                print(f"   - Session 1 response: {response1.content[:50]}...")
            if response2:
                print(f"   - Session 2 response: {response2.content[:50]}...")
            
            # Clean up second session
            self.assistant.delete_sessions(ids=[session2.id])
            print(f"✅ Cleaned up test session")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed session management test: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources"""
        print(f"\n🧹 Cleaning up test resources...")
        
        try:
            if self.test_session and self.assistant:
                self.assistant.delete_sessions(ids=[self.test_session.id])
                print(f"✅ Deleted test session: {self.test_session.id}")
        except Exception as e:
            print(f"⚠️ Warning: Failed to clean up test session: {e}")
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        print("🚀 Starting RAGFlow SDK comprehensive testing")
        print("=" * 60)
        
        tests = [
            ("Connection Test", self.test_connection),
            ("List Assistants", self.test_list_assistants),
            ("Create Session", self.test_create_session),
            ("List Sessions", self.test_list_sessions),
            ("Basic Chat", self.test_basic_chat),
            ("Streaming Chat", self.test_streaming_chat),
            ("Conversation Flow", self.test_conversation_flow),
            ("Session Management", self.test_session_management)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
            
            # Don't continue if critical tests fail
            if test_name in ["Connection Test", "List Assistants"] and not results[test_name]:
                print(f"\n🛑 Critical test '{test_name}' failed. Stopping tests.")
                break
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} | {test_name}")
        
        print("-" * 60)
        print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All tests passed! RAGFlow SDK is working correctly.")
        elif passed >= total * 0.8:
            print("⚠️ Most tests passed. Minor issues detected.")
        else:
            print("❌ Multiple test failures. Check your configuration.")


def main():
    """Main testing function"""
    print("RAGFlow SDK Testing Script")
    print("Testing with existing 'RCSB ChatBot v2' assistant")
    print("-" * 60)
    
    # Initialize tester
    tester = RAGFlowTester(API_KEY, BASE_URL)
    
    try:
        # Run all tests
        results = tester.run_all_tests()
        
        # Print summary
        tester.print_summary(results)
        
        # Return appropriate exit code
        if all(results.values()):
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        return 1
    finally:
        # Always try to clean up
        tester.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)