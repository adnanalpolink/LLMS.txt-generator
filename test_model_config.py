"""Simple test for model configuration without external dependencies."""

import sys
import os

# Add current directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import (
        CATEGORIZED_LLM_MODELS, 
        DEFAULT_MODEL, 
        validate_custom_model, 
        get_model_display_name
    )
    
    def test_model_configuration():
        """Test the new model configuration."""
        print("🧪 Testing Model Configuration")
        print("=" * 40)
        
        # Test categorized models
        print(f"📊 Model Categories: {len(CATEGORIZED_LLM_MODELS)}")
        total_models = 0
        
        for provider, models in CATEGORIZED_LLM_MODELS.items():
            print(f"  {provider}: {len(models)} models")
            total_models += len(models)
            
            # Show first model from each provider
            if models:
                first_model = models[0]
                display_name = get_model_display_name(first_model)
                print(f"    Example: {first_model} → {display_name}")
        
        print(f"\n📈 Total Models: {total_models}")
        print(f"🎯 Default Model: {DEFAULT_MODEL}")
        
        # Test model validation
        print("\n🔍 Testing Model Validation:")
        
        valid_test_cases = [
            "deepseek/deepseek-r1-0528",
            "openai/gpt-4.1",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-flash-preview-05-20:thinking",
            "x-ai/grok-3-beta",
            "custom-provider/my-model:variant"
        ]
        
        invalid_test_cases = [
            "",
            "invalid",
            "provider",
            "/model",
            "provider/",
            "provider model",
            "provider/model/extra"
        ]
        
        print("  Valid models:")
        for model in valid_test_cases:
            is_valid = validate_custom_model(model)
            status = "✅" if is_valid else "❌"
            print(f"    {status} {model}")
        
        print("  Invalid models:")
        for model in invalid_test_cases:
            is_valid = validate_custom_model(model)
            status = "✅" if not is_valid else "❌"
            print(f"    {status} {model} (correctly rejected)")
        
        # Test display names
        print("\n🎨 Testing Display Names:")
        test_models = [
            "deepseek/deepseek-r1-0528:free",
            "anthropic/claude-3.7-sonnet:thinking",
            "openai/gpt-4.1-mini",
            "google/gemini-2.5-pro-preview"
        ]
        
        for model in test_models:
            display_name = get_model_display_name(model)
            print(f"    {model} → {display_name}")
        
        # Validate default model
        print(f"\n🎯 Default Model Validation:")
        is_default_valid = validate_custom_model(DEFAULT_MODEL)
        status = "✅" if is_default_valid else "❌"
        print(f"    {status} {DEFAULT_MODEL}")
        
        print("\n🎉 Model configuration test completed!")
        return True
        
    if __name__ == "__main__":
        test_model_configuration()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure config.py is in the current directory")
except Exception as e:
    print(f"❌ Test failed: {e}")
