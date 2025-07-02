import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .models import BaseModel, ModelResponse, ClaudeModel


class AIOrchestrator:
    """Orchestrates queries to multiple AI models and consolidates responses"""
    
    def __init__(self, models: List[BaseModel], consolidator: BaseModel):
        self.models = models
        self.consolidator = consolidator
    
    async def query_all_models(self, prompt: str, **kwargs) -> List[ModelResponse]:
        """Query all models in parallel"""
        tasks = [
            model.query_with_retry(prompt, **kwargs) 
            for model in self.models
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions that occurred
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                processed_responses.append(
                    ModelResponse(
                        model_name=self.models[i].model_name,
                        response="",
                        metadata={},
                        error=str(response)
                    )
                )
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    async def consolidate_responses(
        self, 
        prompt: str, 
        responses: List[ModelResponse]
    ) -> ModelResponse:
        """Use consolidator model to synthesize all responses"""
        
        # Build consolidation prompt
        consolidation_prompt = self._build_consolidation_prompt(prompt, responses)
        
        # Query consolidator
        consolidated = await self.consolidator.query_with_retry(
            consolidation_prompt,
            temperature=0.5,  # Lower temperature for more focused synthesis
            max_tokens=8192   # Allow longer consolidated response
        )
        
        return consolidated
    
    def _build_consolidation_prompt(self, original_prompt: str, responses: List[ModelResponse]) -> str:
        """Build prompt for consolidation"""
        prompt_parts = [
            "You are tasked with consolidating and synthesizing responses from multiple AI models.",
            "\n\nOriginal prompt:",
            f'"{original_prompt}"',
            "\n\nResponses from different models:"
        ]
        
        for response in responses:
            if response.error:
                prompt_parts.append(
                    f"\n\n### {response.model_name}\n[Error occurred: {response.error}]"
                )
            else:
                prompt_parts.append(
                    f"\n\n### {response.model_name}\n{response.response}"
                )
        
        prompt_parts.extend([
            "\n\nPlease provide a comprehensive synthesis that:",
            "1. Identifies key insights and agreements across models",
            "2. Highlights important differences or unique perspectives",
            "3. Provides a balanced, nuanced final analysis",
            "4. Preserves valuable details while maintaining clarity",
            "\nYour synthesis:"
        ])
        
        return "\n".join(prompt_parts)
    
    async def execute_workflow(
        self, 
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the complete orchestration workflow"""
        
        workflow_start = datetime.utcnow()
        
        # Step 1: Query all models in parallel
        print("Querying all models...")
        responses = await self.query_all_models(prompt, **kwargs)
        
        # Step 2: Consolidate responses
        print("Consolidating responses...")
        consolidated = await self.consolidate_responses(prompt, responses)
        
        workflow_end = datetime.utcnow()
        
        return {
            "prompt": prompt,
            "individual_responses": responses,
            "consolidated_response": consolidated,
            "metadata": {
                "workflow_duration_seconds": (workflow_end - workflow_start).total_seconds(),
                "timestamp": workflow_start.isoformat(),
                "models_queried": [model.model_name for model in self.models],
                "consolidator_model": self.consolidator.model_name
            }
        }
