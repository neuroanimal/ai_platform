#!/usr/bin/env python3
"""
Test script for integrated YAML processing functionality
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.trace_handler import TraceHandler
from engines.orchestrator_engine_v2 import OrchestratorEngine


def test_direct_processing():
    """Test direct YAML processing (uncomment-00 approach)."""
    print("=== Testing Direct YAML Processing ===")
    
    # Initialize
    tracer = TraceHandler("TEST", "1.0", "DirectTest")
    orchestrator = OrchestratorEngine("CCRC", "1.19", {})
    
    try:
        # Test direct processing
        success = orchestrator.run_direct_yaml_process(
            system_size="standard-system"
        )
        
        if success:
            print("✓ Direct processing completed successfully")
        else:
            print("✗ Direct processing failed")
            
    except Exception as e:
        print(f"✗ Direct processing error: {e}")


def test_hybrid_processing():
    """Test hybrid processing (ML + direct)."""
    print("\n=== Testing Hybrid Processing ===")
    
    orchestrator = OrchestratorEngine("CCRC", "1.19", {})
    
    try:
        success = orchestrator.run_hybrid_process(
            system_size="standard-system"
        )
        
        if success:
            print("✓ Hybrid processing completed successfully")
        else:
            print("✗ Hybrid processing failed")
            
    except Exception as e:
        print(f"✗ Hybrid processing error: {e}")


def test_ml_processing():
    """Test original ML-based processing."""
    print("\n=== Testing ML Processing ===")
    
    orchestrator = OrchestratorEngine("CCRC", "1.19", {})
    
    try:
        orchestrator.run_uncomment_process()
        print("✓ ML processing completed")
        
    except Exception as e:
        print(f"✗ ML processing error: {e}")


def main():
    """Run all tests."""
    print("Testing Integrated YAML Processing System")
    print("=" * 50)
    
    # Check if test data exists
    test_data_path = "data/CCRC/1.19/input/template/values.yaml"
    if not os.path.exists(test_data_path):
        print(f"⚠ Test data not found at: {test_data_path}")
        print("Please ensure test data is available or adjust paths in the test.")
        return
    
    test_direct_processing()
    test_hybrid_processing()
    test_ml_processing()
    
    print("\n" + "=" * 50)
    print("Testing completed. Check output files in data/CCRC/1.19/output/template/")


if __name__ == "__main__":
    main()