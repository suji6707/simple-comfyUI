import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4
from enum import Enum
import structlog

logger = structlog.get_logger()


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionContext:
    """
    Context passed between nodes during workflow execution.
    """
    def __init__(self, job_id: str, user_id: str, initial_data: Dict[str, Any] = None):
        self.job_id = job_id
        self.user_id = user_id
        self.data = initial_data or {}
        self.cache = {}
        self.metadata = {}


class WorkflowNode(ABC):
    """
    Abstract base class for all workflow nodes.
    """
    
    def __init__(self, node_id: str, node_type: str, parameters: Dict[str, Any] = None):
        self.node_id = node_id
        self.node_type = node_type
        self.parameters = parameters or {}
        self.status = NodeStatus.PENDING
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.error_message: Optional[str] = None
        
        # Dependencies
        self.input_connections: Dict[str, Tuple[str, str]] = {}  # {input_key: (source_node_id, source_output_key)}
        self.output_connections: Dict[str, List[Tuple[str, str]]] = {}  # {output_key: [(target_node_id, target_input_key)]}

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute the node and return outputs.
        """
        pass

    def add_input_connection(self, input_key: str, source_node_id: str, source_output_key: str):
        """
        Connect an input to another node's output.
        """
        self.input_connections[input_key] = (source_node_id, source_output_key)

    def add_output_connection(self, output_key: str, target_node_id: str, target_input_key: str):
        """
        Connect an output to another node's input.
        """
        if output_key not in self.output_connections:
            self.output_connections[output_key] = []
        self.output_connections[output_key].append((target_node_id, target_input_key))

    async def run(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Run the node with error handling and status tracking.
        """
        try:
            self.status = NodeStatus.RUNNING
            logger.info(f"Executing node {self.node_id} ({self.node_type})")
            
            outputs = await self.execute(context)
            self.outputs = outputs
            self.status = NodeStatus.COMPLETED
            
            logger.info(f"Node {self.node_id} completed successfully")
            return outputs
            
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.error_message = str(e)
            logger.error(f"Node {self.node_id} failed: {e}", exc_info=e)
            raise


class PromptEnhancementNode(WorkflowNode):
    """
    Node that enhances user prompts with style-specific additions.
    """
    
    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        base_prompt = self.inputs.get("prompt", context.data.get("prompt", ""))
        style_prompts = self.parameters.get("style_prompts", [])
        negative_prompt = self.parameters.get("negative_prompt", "")
        
        # Enhance the prompt
        enhanced_prompt = base_prompt
        if style_prompts:
            style_text = ", ".join(style_prompts)
            enhanced_prompt = f"{base_prompt}, {style_text}"
        
        return {
            "enhanced_prompt": enhanced_prompt,
            "negative_prompt": negative_prompt,
            "original_prompt": base_prompt
        }


class GenerationNode(WorkflowNode):
    """
    Node that performs AI image generation.
    """
    
    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        # 이전 노드에서 받은 입력
        prompt = self.inputs.get("enhanced_prompt", self.inputs.get("prompt", context.data.get("prompt")))
        negative_prompt = self.inputs.get("negative_prompt", self.parameters.get("negative_prompt", ""))
        
        # Get generation parameters
        width = self.parameters.get("width", 1024)
        height = self.parameters.get("height", 1024)
        steps = self.parameters.get("steps", 50)
        cfg_scale = self.parameters.get("cfg_scale", 7.5)
        scheduler = self.parameters.get("scheduler", "DPMSolverMultistep")
        model = self.parameters.get("model", "stabilityai/stable-diffusion-xl-base-1.0")
        
        # TODO: Implement actual model inference
        # For now, return mock data
        return {
            "generated_images": [
                {
                    "image_data": f"mock_image_data_{uuid4()}",
                    "seed": 12345,
                    "model_used": model,
                    "generation_time": 30.5
                }
            ],
            "generation_metadata": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "scheduler": scheduler
            }
        }


class ImageInputNode(WorkflowNode):
    """
    Node that handles image input for img2img workflows.
    """
    
    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        input_type = self.parameters.get("input_type", "image")
        preprocessing = self.parameters.get("preprocessing", "none")
        
        # Get image data from context or inputs
        image_data = self.inputs.get("image_data", context.data.get("input_image"))
        
        if not image_data:
            raise ValueError("No input image provided")
        
        # TODO: Implement image preprocessing
        processed_image = image_data
        
        return {
            "processed_image": processed_image,
            "original_image": image_data,
            "preprocessing_applied": preprocessing
        }


class UpscalingNode(WorkflowNode):
    """
    Node that upscales generated images.
    """
    
    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        images = self.inputs.get("generated_images", [])
        scale_factor = self.parameters.get("scale_factor", 2)
        upscaler_model = self.parameters.get("upscaler_model", "RealESRGAN_x4plus")
        
        if not images:
            raise ValueError("No images to upscale")
        
        # TODO: Implement actual upscaling
        upscaled_images = []
        for image in images:
            upscaled_images.append({
                **image,
                "upscaled": True,
                "scale_factor": scale_factor,
                "upscaler_model": upscaler_model
            })
        
        return {
            "upscaled_images": upscaled_images,
            "original_images": images
        }


class SaveImageNode(WorkflowNode):
    """
    Node that saves generated images to storage.
    """
    
    async def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        images = self.inputs.get("generated_images", self.inputs.get("upscaled_images", []))
        
        if not images:
            raise ValueError("No images to save")
        
        # TODO: Implement actual image saving to S3
        saved_images = []
        for i, image in enumerate(images):
            image_url = f"https://example.com/images/{context.job_id}_{i}.jpg"
            thumbnail_url = f"https://example.com/thumbnails/{context.job_id}_{i}.jpg"
            
            saved_images.append({
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "metadata": image.get("generation_metadata", {})
            })
        
        return {
            "saved_images": saved_images,
            "image_count": len(saved_images)
        }


class WorkflowEngine:
    """
    Main workflow execution engine that manages node-based workflows.
    """
    
    def __init__(self):
        self.node_registry: Dict[str, type] = {
            "prompt_enhancement": PromptEnhancementNode,
            "generation": GenerationNode,
            "image_input": ImageInputNode,
            "img2img_generation": GenerationNode,  # Same as generation but with image input
            "upscaling": UpscalingNode,
            "save_image": SaveImageNode,
        }

    def create_workflow_from_config(self, config: Dict[str, Any]) -> 'Workflow':
        """
        Create a workflow from configuration.
        """
        workflow = Workflow()
        
        # Get pipeline configuration
        pipeline = config.get("pipeline", [])
        
        # Create nodes from pipeline
        previous_node_id = None
        for i, node_config in enumerate(pipeline):
            node_type = node_config["node_type"]
            node_id = f"{node_type}_{i}"
            parameters = node_config.get("parameters", {})
            
            # Add global config parameters
            if node_type == "generation" or node_type == "img2img_generation":
                parameters.update({
                    "width": config.get("width", 1024),
                    "height": config.get("height", 1024),
                    "steps": config.get("steps", 50),
                    "cfg_scale": config.get("cfg_scale", 7.5),
                    "scheduler": config.get("scheduler", "DPMSolverMultistep"),
                    "model": config.get("model", "stabilityai/stable-diffusion-xl-base-1.0")
                })
            
            # Create node
            node = self.create_node(node_id, node_type, parameters)
            workflow.add_node(node)
            
            # Connect to previous node if it exists
            if previous_node_id and i > 0:
                self._auto_connect_nodes(workflow, previous_node_id, node_id)
            
            previous_node_id = node_id
        
        # Add save node at the end
        save_node = self.create_node("save_output", "save_image", {})
        workflow.add_node(save_node)
        
        if previous_node_id:
            self._auto_connect_nodes(workflow, previous_node_id, "save_output")
        
        return workflow

    def create_node(self, node_id: str, node_type: str, parameters: Dict[str, Any]) -> WorkflowNode:
        """
        Create a node instance from type and parameters.
        """
        if node_type not in self.node_registry:
            raise ValueError(f"Unknown node type: {node_type}")
        
        node_class = self.node_registry[node_type]
        return node_class(node_id, node_type, parameters)

    def _auto_connect_nodes(self, workflow: 'Workflow', source_node_id: str, target_node_id: str):
        """
        Automatically connect compatible outputs to inputs between nodes.
        """
        source_node = workflow.nodes[source_node_id]
        target_node = workflow.nodes[target_node_id]
        
        # Simple auto-connection rules
        connection_rules = {
            ("prompt_enhancement", "generation"): [("enhanced_prompt", "enhanced_prompt"), ("negative_prompt", "negative_prompt")],
            ("prompt_enhancement", "img2img_generation"): [("enhanced_prompt", "enhanced_prompt"), ("negative_prompt", "negative_prompt")],
            ("image_input", "img2img_generation"): [("processed_image", "input_image")],
            ("generation", "upscaling"): [("generated_images", "generated_images")],
            ("img2img_generation", "upscaling"): [("generated_images", "generated_images")],
            ("generation", "save_image"): [("generated_images", "generated_images")],
            ("img2img_generation", "save_image"): [("generated_images", "generated_images")],
            ("upscaling", "save_image"): [("upscaled_images", "generated_images")],
        }
        
        key = (source_node.node_type, target_node.node_type)
        if key in connection_rules:
            for output_key, input_key in connection_rules[key]:
                workflow.connect_nodes(source_node_id, output_key, target_node_id, input_key)


class Workflow:
    """
    Represents a complete workflow with nodes and connections.
    """
    
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.execution_order: List[str] = []

    def add_node(self, node: WorkflowNode):
        """
        Add a node to the workflow.
        """
        self.nodes[node.node_id] = node

    def connect_nodes(self, source_node_id: str, output_key: str, target_node_id: str, input_key: str):
        """
        Connect two nodes.
        """
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            raise ValueError("Source or target node not found")
        
        source_node = self.nodes[source_node_id]
        target_node = self.nodes[target_node_id]
        
        source_node.add_output_connection(output_key, target_node_id, input_key)
        target_node.add_input_connection(input_key, source_node_id, output_key)

    def _topological_sort(self) -> List[str]:
        """
        Perform topological sort to determine execution order.
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        
        # Calculate in-degrees
        for node_id, node in self.nodes.items():
            in_degree[node_id] = len(node.input_connections)
        
        # Find nodes with no dependencies
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Update in-degrees for connected nodes
            for output_key, connections in self.nodes[current].output_connections.items():
                for target_node_id, target_input_key in connections:
                    in_degree[target_node_id] -= 1
                    if in_degree[target_node_id] == 0:
                        queue.append(target_node_id)
        
        if len(result) != len(self.nodes):
            raise ValueError("Circular dependency detected in workflow")
        
        return result

    async def execute(self, context: ExecutionContext, progress_callback=None) -> Dict[str, Any]:
        """
        Execute the entire workflow.
        """
        logger.info(f"Starting workflow execution for job {context.job_id}")
        
        # Determine execution order
        self.execution_order = self._topological_sort()
        total_nodes = len(self.execution_order)
        
        # Execute nodes in order
        for i, node_id in enumerate(self.execution_order):
            node = self.nodes[node_id]
            
            # Prepare node inputs from connected outputs
            for input_key, (source_node_id, source_output_key) in node.input_connections.items():
                source_node = self.nodes[source_node_id]
                if source_node.status != NodeStatus.COMPLETED:
                    raise RuntimeError(f"Source node {source_node_id} not completed")
                
                if source_output_key in source_node.outputs:
                    node.inputs[input_key] = source_node.outputs[source_output_key]
            
            # Execute node
            try:
                await node.run(context)
                
                # Report progress
                if progress_callback:
                    progress = int((i + 1) / total_nodes * 100)
                    await progress_callback(progress, f"Completed {node.node_type}")
                    
            except Exception as e:
                logger.error(f"Workflow execution failed at node {node_id}", exc_info=e)
                if progress_callback:
                    await progress_callback(0, f"Failed at {node.node_type}: {str(e)}")
                raise
        
        # Get final outputs from the last node
        if self.execution_order:
            final_node = self.nodes[self.execution_order[-1]]
            final_outputs = final_node.outputs
        else:
            final_outputs = {}
        
        logger.info(f"Workflow execution completed for job {context.job_id}")
        return final_outputs