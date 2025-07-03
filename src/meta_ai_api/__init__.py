__version__ = "1.2.5"

# Import the main client classes
from .main import MetaAI  # Legacy interface for backward compatibility
from .client import MetaAI as MetaAIClient  # New refactored interface
from .cli import MetaAICLI  # CLI interface

# Export both interfaces and CLI
__all__ = ["MetaAI", "MetaAIClient", "MetaAICLI"]
